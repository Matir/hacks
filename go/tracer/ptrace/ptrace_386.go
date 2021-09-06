package ptrace

import (
	"syscall"
)

func getSyscallArgByPosition(regs *syscall.PtraceRegs, pos int) uint32 {
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
