package ptrace

import (
	"math"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

func getSyscallArgByPosition(regs *syscall.PtraceRegs, pos int) int32 {
	switch pos {
	case 0:
		return regs.Ebx
	case 1:
		return regs.Ecx
	case 2:
		return regs.Edx
	case 3:
		return regs.Esi
	case 4:
		return regs.Edi
	case 5:
		return regs.Ebp
	default:
		logger.Fatalf("Unsupported syscall arg position: %d", pos)
	}
	return 0 // for static analysis
}

func decodeTraceEvent(pid int, regs *syscall.PtraceRegs, start *TraceEvent) *TraceEvent {
	getErrno := func(p uint32) int {
		eMin := uint32(math.MaxUint32 - ERRNO_MAX)
		if uint32(p) < eMin {
			return 0
		}
		return -int(p)
	}
	rv := &TraceEvent{
		Pid:       pid,
		PC:        uint64(regs.Eip),
		Timestamp: time.Now(),
	}
	if start != nil {
		rv.SyscallExit = true
		rv.SyscallNum = start.SyscallNum
		if en := getErrno(uint32(regs.Eax)); en == 0 {
			rv.SyscallReturn = uint64(regs.Eax)
		} else {
			rv.SyscallErrno = syscall.Errno(en)
			rv.SyscallReturnName = unix.ErrnoName(syscall.Errno(en))
		}
		extractArgs(pid, regs, &rv.PostcallArgs)
		rv.PrecallArgs = start.PrecallArgs
		// TODO: make this more straightforward
		rv.Argv = start.Argv
	} else {
		rv.SyscallNum = uint64(regs.Orig_eax)
		extractArgs(pid, regs, &rv.PrecallArgs)
	}
	// Special case decoding
	if handler, ok := SyscallHandlers[rv.SyscallNum]; ok {
		handler(rv)
	}
	return rv
}
