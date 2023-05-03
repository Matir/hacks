package ptrace

import (
	"math"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

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
		logger.Fatalf("Unsupported syscall arg position: %d", pos)
	}
	return 0 // for static analysis
}

func decodeTraceEvent(pid int, regs *syscall.PtraceRegs, start *TraceEvent) *TraceEvent {
	getErrno := func(p uint64) int {
		eMin := uint64(math.MaxUint64 - ERRNO_MAX)
		if uint64(p) < eMin {
			return 0
		}
		return -int(p)
	}
	rv := &TraceEvent{
		Pid:       pid,
		PC:        regs.Rip,
		Timestamp: time.Now(),
	}
	if start != nil {
		rv.SyscallExit = true
		rv.SyscallNum = start.SyscallNum
		if en := getErrno(regs.Rax); en == 0 {
			rv.SyscallReturn = regs.Rax
		} else {
			rv.SyscallErrno = syscall.Errno(en)
			rv.SyscallReturnName = unix.ErrnoName(syscall.Errno(en))
		}
		extractArgs(pid, regs, &rv.PostcallArgs)
		rv.PrecallArgs = start.PrecallArgs
		// TODO: make this more straightforward
		rv.Argv = start.Argv
	} else {
		rv.SyscallNum = regs.Orig_rax
		extractArgs(pid, regs, &rv.PrecallArgs)
	}
	// Special case decoding
	if handler, ok := SyscallHandlers[rv.SyscallNum]; ok {
		handler(rv)
	}
	return rv
}
