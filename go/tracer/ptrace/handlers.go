package ptrace

import (
	"syscall"
)

var SyscallHandlers = make(map[uint64]func(*TraceEvent) error)

func SyscallExecveHandler(te *TraceEvent) error {
	if !te.SyscallExit {
		te.Argv = readStringArray(te.Pid, uintptr(te.PrecallArgs[1].Value))
	}
	return nil
}

func init() {
	SyscallHandlers[syscall.SYS_EXECVE] = SyscallExecveHandler
}
