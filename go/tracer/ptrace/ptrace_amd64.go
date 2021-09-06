package ptrace

import (
	"syscall"
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
