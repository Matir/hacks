package ptrace

//go:generate bash ./buildsyscalls.sh

type SyscallMeta struct {
	SyscallName string
	NumArgs     int
}
