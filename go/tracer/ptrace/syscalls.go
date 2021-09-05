package ptrace

//go:generate bash ./buildsyscalls.sh

import (
	"fmt"
)

type SyscallMeta struct {
	SyscallName string
	NumArgs     int
}

func GetMeta(scnum int) SyscallMeta {
	if m, ok := SyscallMetadata[scnum]; ok {
		return m
	}
	return SyscallMeta{
		SyscallName: fmt.Sprintf("SYS_%d", scnum),
		NumArgs:     6,
	}
}
