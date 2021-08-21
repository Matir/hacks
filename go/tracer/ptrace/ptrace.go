package ptrace

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"runtime"
	"syscall"

	seccomp "github.com/seccomp/libseccomp-golang"
	"golang.org/x/sys/unix"
)

const (
	PEEK_BYTES_ARG   = 1024
	MAX_SYSCALL_ARGS = 7
)

var logger = log.New(os.Stderr, "", log.LstdFlags)

type TraceArg struct {
	Value      uint64
	BytesValue []byte
}

type TraceArgs [MAX_SYSCALL_ARGS]TraceArg

type TraceEvent struct {
	Pid           int
	SyscallExit   bool
	SyscallNum    uint64
	SyscallReturn uint64
	PrecallArgs   TraceArgs
	PostcallArgs  TraceArgs
	PC            uint64
}

func TraceProcess(args []string) (<-chan *TraceEvent, error) {
	errChan := make(chan error)
	resChan := make(chan *TraceEvent, 10) //Arbitrary capacity

	go traceProcessInternal(args, resChan, errChan)

	return resChan, <-errChan
}

func traceProcessInternal(args []string, evts chan<- *TraceEvent, errs chan<- error) {
	defer close(errs)
	defer close(evts)
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	pendingSyscalls := make(map[int]*TraceEvent)
	knownProcs := make(map[int]bool)

	// Ok, start the real work here
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Ptrace: true,
	}
	if err := cmd.Start(); err != nil {
		logger.Printf("Error starting process: %s", err)
		errs <- err
		return
	}
	// Wait for started, this is *not* the process being done
	cmd.Wait()

	opts := unix.PTRACE_O_EXITKILL
	opts |= syscall.PTRACE_O_TRACECLONE
	opts |= syscall.PTRACE_O_TRACEFORK
	opts |= syscall.PTRACE_O_TRACEVFORK
	if err := syscall.PtraceSetOptions(cmd.Process.Pid, opts); err != nil {
		logger.Printf("Error with PtraceSetOptions: %s", err)
		cmd.Process.Kill()
		errs <- err
		return
	}

	errs <- nil

	traceePid := cmd.Process.Pid
	knownProcs[traceePid] = true

	// Now actually trace stuff
	for {
		if traceePid != 0 {
			if err := syscall.PtraceSyscall(traceePid, 0); err != nil {
				logger.Printf("Error in PtraceSyscall: %s", err)
				break
			}
		}

		// wait for a child signal?
		var ws syscall.WaitStatus
		if childPid, err := syscall.Wait4(-1, &ws, 0, nil); err != nil {
			logger.Printf("Error in Wait4: %s", err)
			break
		} else {
			traceePid = childPid
			knownProcs[traceePid] = true
		}

		//logger.Printf("Wait signal, stopped, exited: %s, %v, %v", ws.Signal(), ws.Stopped(), ws.Exited())

		if ws.Exited() {
			// Don't bother, maybe we should race a trace event at some point in the
			// future?
			delete(knownProcs, traceePid)
			if len(knownProcs) == 0 {
				// Not tracing any more children
				break
			}
			traceePid = 0
			continue
		}

		var pendingSyscall *TraceEvent
		if pend, ok := pendingSyscalls[traceePid]; ok {
			pendingSyscall = pend
		}

		var regs syscall.PtraceRegs
		if err := syscall.PtraceGetRegs(traceePid, &regs); err != nil {
			logger.Printf("Error in PtraceGetRegs[%d]: %s", traceePid, err)
			break
		}
		tevent := DecodeTraceEvent(traceePid, &regs, pendingSyscall)
		evts <- tevent
		if pendingSyscall == nil {
			// Must be a new syscall, put in map
			pendingSyscalls[traceePid] = tevent
		} else {
			delete(pendingSyscalls, traceePid)
		}
	}
}

func (te *TraceEvent) String() string {
	dir := "->"
	rv := ""
	if te.SyscallExit {
		dir = "<-"
		rv = fmt.Sprintf(" = %d", te.SyscallReturn)
	}
	// TODO: custom formatting per syscall
	args := fmt.Sprintf(
		"%#x, %#x, %#x, %#x, %#x, %#x",
		te.PrecallArgs[0].Value,
		te.PrecallArgs[1].Value,
		te.PrecallArgs[2].Value,
		te.PrecallArgs[3].Value,
		te.PrecallArgs[4].Value,
		te.PrecallArgs[5].Value,
	)
	return fmt.Sprintf("[%d] %s %d %s (%s)%s", te.Pid, dir, te.SyscallNum, te.SyscallName(), args, rv)
}

func (te *TraceEvent) SyscallName() string {
	if name, err := seccomp.ScmpSyscall(te.SyscallNum).GetName(); err == nil {
		return name
	} else {
		return fmt.Sprintf("SYS_%d", te.SyscallNum)
	}
}

// TODO: make this architecture-independent
func DecodeTraceEvent(pid int, regs *syscall.PtraceRegs, start *TraceEvent) *TraceEvent {
	rv := &TraceEvent{
		Pid: pid,
		PC:  regs.Rip,
	}
	if start != nil {
		rv.SyscallExit = true
		rv.SyscallNum = start.SyscallNum
		rv.SyscallReturn = regs.Rax
		extractArgs(pid, regs, &rv.PostcallArgs)
		rv.PrecallArgs = start.PrecallArgs
	} else {
		rv.SyscallNum = regs.Orig_rax
		extractArgs(pid, regs, &rv.PrecallArgs)
	}
	return rv
}

func extractArgs(pid int, regs *syscall.PtraceRegs, args *TraceArgs) {
	for i := 0; i < 6; i++ {
		scVal := getSyscallArgByPosition(regs, i)
		args[i].Value = scVal
		// Try reading bytes
		storage := make([]byte, PEEK_BYTES_ARG)
		if count, err := syscall.PtracePeekData(pid, uintptr(scVal), storage); err == nil {
			args[i].BytesValue = storage[:count]
		} else {
			// Probably just not a pointer, do we need to do anything?
			if errno, ok := err.(syscall.Errno); ok {
				if errno != syscall.EIO {
					logger.Printf("Error peeking: %s (%d)", err, uint32(errno)) // Just for debugging
				}
			} else {
				logger.Printf("Error peeking: %s", err) // Just for debugging
			}
			args[i].BytesValue = nil
		}

	}
}

func getSyscallArgByPosition(regs *syscall.PtraceRegs, pos int) uint64 {
	switch pos {
	case 0:
		return regs.Rdi
	case 1:
		return regs.Rsi
	case 2:
		return regs.Rdx
	case 3:
		return regs.R10
	case 4:
		return regs.R8
	case 5:
		return regs.R9
	default:
		logger.Fatal("Unsupported syscall arg position: %d", pos)
	}
	return 0 // for static analysis
}
