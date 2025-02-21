package ptrace

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"log"
	"os"
	"os/exec"
	"runtime"
	"syscall"
	"time"
	"unicode/utf8"
	"unsafe"

	seccomp "github.com/seccomp/libseccomp-golang"
	"golang.org/x/sys/unix"
)

const (
	PEEK_BYTES_ARG   = 1024
	MAX_SYSCALL_ARGS = 7
	ERRNO_MAX        = 4095
)

var logger = log.New(os.Stderr, "", log.LstdFlags)

type TraceEventCallback func(*TraceEvent)

type TraceOptionSet struct {
	CloseStdio          bool
	TraceEventCallbacks []TraceEventCallback
}

type TraceOpt func(*TraceOptionSet) error

type TraceArg struct {
	Value      uint64
	BytesValue []byte
}

type TraceArgs [MAX_SYSCALL_ARGS]TraceArg

type TraceEvent struct {
	Pid               int
	Timestamp         time.Time
	SyscallExit       bool
	SyscallNum        uint64
	SyscallReturn     uint64
	SyscallErrno      syscall.Errno
	SyscallReturnName string
	PrecallArgs       TraceArgs
	PostcallArgs      TraceArgs
	PC                uint64
	// Special case
	Argv [][]byte
}

func TraceProcess(args []string) (<-chan *TraceEvent, error) {
	errChan := make(chan error)
	resChan := make(chan *TraceEvent, 10) //Arbitrary capacity
	opts := &TraceOptionSet{}

	go traceProcessInternal(args, opts, resChan, errChan)

	return resChan, <-errChan
}

func TraceProcessWithOptions(args []string, traceOpts ...TraceOpt) (<-chan *TraceEvent, error) {
	opts := &TraceOptionSet{}
	for _, o := range traceOpts {
		if err := o(opts); err != nil {
			return nil, err
		}
	}
	errChan := make(chan error)
	resChan := make(chan *TraceEvent, 10)

	go traceProcessInternal(args, opts, resChan, errChan)

	return resChan, <-errChan
}

func traceProcessInternal(args []string, opts *TraceOptionSet, evts chan<- *TraceEvent, errs chan<- error) {
	defer close(errs)
	defer close(evts)
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	pendingSyscalls := make(map[int]*TraceEvent)
	knownProcs := make(map[int]bool)

	// Ok, start the real work here
	cmd := exec.Command(args[0], args[1:]...)
	if opts.CloseStdio {
		cmd.Stdin = nil
		cmd.Stdout = nil
		cmd.Stderr = nil
	} else {
		cmd.Stdin = os.Stdin
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
	}
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

	ptops := unix.PTRACE_O_EXITKILL
	ptops |= syscall.PTRACE_O_TRACECLONE
	ptops |= syscall.PTRACE_O_TRACEFORK
	ptops |= syscall.PTRACE_O_TRACEVFORK
	ptops |= syscall.PTRACE_O_TRACEEXEC
	ptops |= syscall.PTRACE_O_TRACESYSGOOD
	if err := syscall.PtraceSetOptions(cmd.Process.Pid, ptops); err != nil {
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

		// May need to check event type?
		if ws.StopSignal() != syscall.SIGTRAP|0x80 {
			// Not a syscall trap, handle specially?
			//fmt.Printf("Stop sig: %d\n", ws.StopSignal())
			//fmt.Printf("Trap cause: %d\n", ws.TrapCause())
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
		//fmt.Printf("Regs: %#v\n", regs)
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
		rv = fmt.Sprintf(" = %#x", te.SyscallReturn)
		if te.SyscallReturnName != "" {
			rv = fmt.Sprintf(" = -1 (%s)", te.SyscallReturnName)
		}
	}
	args := defaultArgStringer(te)
	// Custom formatting for certain syscalls
	if stringer, ok := SyscallArgStringers[te.SyscallNum]; ok {
		args = stringer(te)
	}
	return fmt.Sprintf("[%d] %s %d %s (%s)%s", te.Pid, dir, te.SyscallNum, te.SyscallName(), args, rv)
}

func (te *TraceEvent) SyscallName() string {
	if name, err := seccomp.ScmpSyscall(te.SyscallNum).GetName(); err == nil {
		return name
	} else {
		return fmt.Sprintf("SYS_%d", te.SyscallNum)
	}
}

func (ta TraceArg) String() string {
	// Attempt to interpret as a utf-8 encoded c-string starting at this point
	bv := ta.BytesValue
	if idx := bytes.IndexByte(bv, byte(0)); idx != -1 {
		bv = bv[:idx]
	}
	sv := string(bv)
	if utf8.ValidString(sv) {
		return sv
	}
	return ""
}

func DecodeTraceEvent(pid int, regs *syscall.PtraceRegs, start *TraceEvent) *TraceEvent {
	return decodeTraceEvent(pid, regs, start)
}

func extractArgs(pid int, regs *syscall.PtraceRegs, args *TraceArgs) {
	for i := 0; i < 6; i++ {
		// We use uint64 no matter register width
		scVal := uint64(getSyscallArgByPosition(regs, i))
		args[i].Value = scVal
		// Try reading bytes
		if storage, err := peekMemoryHelper(pid, uintptr(scVal)); err == nil {
			args[i].BytesValue = storage
		} else {
			args[i].BytesValue = nil
		}
	}
}

func readStringArray(pid int, addr uintptr) [][]byte {
	ptrstorage, err := peekMemoryHelper(pid, addr)
	if err != nil {
		logger.Printf("Error reading string array pointer: %s", err)
		return nil
	}
	// Extract the list of pointers
	ptrSize := int(unsafe.Sizeof(addr))
	res := make([][]byte, 0)
	buf := bytes.NewBuffer(ptrstorage)
	for i := 0; i < len(ptrstorage)/ptrSize; i++ {
		// TODO: make architecture independent
		var ptr uint64
		if err := binary.Read(buf, binary.LittleEndian, &ptr); err != nil {
			logger.Printf("Error getting pointer: %s", err)
			break
		}
		if ptr == 0 {
			// Null at end of array
			break
		}
		strbuf, err := peekMemoryHelper(pid, uintptr(ptr))
		if err != nil {
			break
		}
		res = append(res, strbuf)
	}
	return res
}

func peekMemoryHelper(pid int, addr uintptr) ([]byte, error) {
	if addr == 0 {
		return nil, nil
	}
	storage := make([]byte, PEEK_BYTES_ARG)
	if count, err := syscall.PtracePeekData(pid, addr, storage); err == nil {
		return storage[:count], nil
	} else {
		// Probably just not a pointer, do we need to do anything?
		if errno, ok := err.(syscall.Errno); ok {
			if errno != syscall.EIO {
				logger.Printf("Error peeking: %s (%d)", err, uint32(errno)) // Just for debugging
				return nil, err
			}
		} else {
			logger.Printf("Error peeking: %s", err) // Just for debugging
			return nil, err
		}
	}
	// Nil error when we can't deref
	return nil, nil
}

// Specify to close STDIO instead of using defaults
func WithCloseStdio(tos *TraceOptionSet) error {
	tos.CloseStdio = true
	return nil
}

// With callback
func WithCallback(f TraceEventCallback) TraceOpt {
	return func(tos *TraceOptionSet) error {
		tos.TraceEventCallbacks = append(tos.TraceEventCallbacks, f)
		return nil
	}
}
