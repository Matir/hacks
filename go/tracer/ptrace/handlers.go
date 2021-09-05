package ptrace

import (
	"bytes"
	"fmt"
	"strings"
	"syscall"
)

type SyscallInfoHandler func(*TraceEvent) error
type SyscallArgStringer func(*TraceEvent) string

var SyscallHandlers = make(map[uint64]SyscallInfoHandler)
var SyscallArgStringers = make(map[uint64]SyscallArgStringer)

func SyscallExecveHandler(te *TraceEvent) error {
	if !te.SyscallExit {
		te.Argv = readStringArray(te.Pid, uintptr(te.PrecallArgs[1].Value))
	}
	return nil
}

func defaultArgStringer(te *TraceEvent) string {
	meta := GetMeta(int(te.SyscallNum))
	argv := make([]string, meta.NumArgs)
	for i := 0; i < meta.NumArgs; i++ {
		argv[i] = fmt.Sprintf("%#x", te.PrecallArgs[i].Value)
	}
	return strings.Join(argv, ", ")
}

func SyscallExecveStringer(te *TraceEvent) string {
	argv := make([]string, len(te.Argv))
	for i := 0; i < len(te.Argv); i++ {
		arg := te.Argv[i]
		if pos := bytes.IndexByte(arg, byte(0)); pos != -1 {
			arg = arg[:pos]
		}
		argv[i] = string(arg)
	}
	argvStr := strings.Join(argv, ", ")
	pathName := te.PrecallArgs[0].BytesValue
	if pos := bytes.IndexByte(pathName, byte(0)); pos != -1 {
		pathName = pathName[:pos]
	}
	return fmt.Sprintf("%s, [%s]", string(pathName), argvStr)
}

func init() {
	SyscallHandlers[syscall.SYS_EXECVE] = SyscallExecveHandler
	SyscallArgStringers[syscall.SYS_EXECVE] = SyscallExecveStringer
}
