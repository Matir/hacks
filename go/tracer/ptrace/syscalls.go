package ptrace

//go:generate bash ./buildsyscalls.sh

import (
	"fmt"
	"log"
	"strings"
)

const (
	IntSize = 32 << (^uint(0) >> 63)
)

type SyscallMeta struct {
	SyscallName string
	NumArgs     int
	ArgInfo     []SyscallArgInfo
}

type SyscallArgInfo struct {
	KernelType string
	Pointer    bool
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

func extractArgInfo(info *SyscallArgInfo) error {
	if info.KernelType == "" {
		return nil
	}
	ktype := strings.ReplaceAll(info.KernelType, "__user", "")
	ktype = strings.ReplaceAll(ktype, "  ", " ")
	info.Pointer = describesPointer(ktype)
	return nil
}

func describesPointer(ktype string) bool {
	if strings.HasSuffix(ktype, "*") {
		return true
	}
	switch ktype {
	case "int", "pid_t", "uid_t", "gid_t", "unsigned int", "unsigned long", "size_t", "long", "off_t", "umode_t", "loff_t", "timer_t", "unsigned", "u64", "mode_t", "clockid_t", "__u64", "__s32", "mqd_t", "key_t", "aio_context_t", "rwf_t", "qid_t", "key_serial_t":
		return false
	case "cap_user_header_t", "cap_user_data_t":
		return true
	default:
		log.Printf("%q is unknown pointer state", ktype)
		return false
	}
}

func init() {
	// Update the SyscallMetadata table
	for _, e := range SyscallMetadata {
		for _, arg := range e.ArgInfo {
			if err := extractArgInfo(&arg); err != nil {
				// todo: handle more gracefully
				panic(err)
			}
		}
	}
}
