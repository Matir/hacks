package ptrace

var SyscallMetadata = map[int]SyscallMeta{
	0: SyscallMeta{SyscallName: "restart_syscall", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	1: SyscallMeta{SyscallName: "exit", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	2: SyscallMeta{SyscallName: "fork", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	3: SyscallMeta{SyscallName: "read", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	4: SyscallMeta{SyscallName: "write", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	5: SyscallMeta{SyscallName: "open", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "umode_t"},
	}},
	6: SyscallMeta{SyscallName: "close", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	7: SyscallMeta{SyscallName: "waitpid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	8: SyscallMeta{SyscallName: "creat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	9: SyscallMeta{SyscallName: "link", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	10: SyscallMeta{SyscallName: "unlink", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	11: SyscallMeta{SyscallName: "execve", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "char __user * __user *"},
	}},
	12: SyscallMeta{SyscallName: "chdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	13: SyscallMeta{SyscallName: "time", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "old_time_t __user *"},
	}},
	14: SyscallMeta{SyscallName: "mknod", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
		{KernelType: "unsigned"},
	}},
	15: SyscallMeta{SyscallName: "chmod", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	16: SyscallMeta{SyscallName: "lchown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	17: SyscallMeta{SyscallName: "break", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	18: SyscallMeta{SyscallName: "oldstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	19: SyscallMeta{SyscallName: "lseek", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "off_t"},
		{KernelType: "unsigned int"},
	}},
	20: SyscallMeta{SyscallName: "getpid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	21: SyscallMeta{SyscallName: "mount", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "void __user *"},
	}},
	22: SyscallMeta{SyscallName: "umount", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	23: SyscallMeta{SyscallName: "setuid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
	}},
	24: SyscallMeta{SyscallName: "getuid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	25: SyscallMeta{SyscallName: "stime", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "old_time_t __user *"},
	}},
	26: SyscallMeta{SyscallName: "ptrace", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	27: SyscallMeta{SyscallName: "alarm", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	28: SyscallMeta{SyscallName: "oldfstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	29: SyscallMeta{SyscallName: "pause", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	30: SyscallMeta{SyscallName: "utime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct utimbuf __user *"},
	}},
	31: SyscallMeta{SyscallName: "stty", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	32: SyscallMeta{SyscallName: "gtty", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	33: SyscallMeta{SyscallName: "access", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	34: SyscallMeta{SyscallName: "nice", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	35: SyscallMeta{SyscallName: "ftime", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	36: SyscallMeta{SyscallName: "sync", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	37: SyscallMeta{SyscallName: "kill", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	38: SyscallMeta{SyscallName: "rename", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	39: SyscallMeta{SyscallName: "mkdir", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	40: SyscallMeta{SyscallName: "rmdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	41: SyscallMeta{SyscallName: "dup", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	42: SyscallMeta{SyscallName: "pipe", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
	}},
	43: SyscallMeta{SyscallName: "times", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct tms __user *"},
	}},
	44: SyscallMeta{SyscallName: "prof", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	45: SyscallMeta{SyscallName: "brk", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
	}},
	46: SyscallMeta{SyscallName: "setgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
	}},
	47: SyscallMeta{SyscallName: "getgid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	48: SyscallMeta{SyscallName: "signal", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "__sighandler_t"},
	}},
	49: SyscallMeta{SyscallName: "geteuid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	50: SyscallMeta{SyscallName: "getegid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	51: SyscallMeta{SyscallName: "acct", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	52: SyscallMeta{SyscallName: "umount2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	53: SyscallMeta{SyscallName: "lock", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	54: SyscallMeta{SyscallName: "ioctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	55: SyscallMeta{SyscallName: "fcntl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	56: SyscallMeta{SyscallName: "mpx", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	57: SyscallMeta{SyscallName: "setpgid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
	}},
	58: SyscallMeta{SyscallName: "ulimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	59: SyscallMeta{SyscallName: "oldolduname", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	60: SyscallMeta{SyscallName: "umask", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	61: SyscallMeta{SyscallName: "chroot", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	62: SyscallMeta{SyscallName: "ustat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned"},
		{KernelType: "struct ustat __user *"},
	}},
	63: SyscallMeta{SyscallName: "dup2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	64: SyscallMeta{SyscallName: "getppid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	65: SyscallMeta{SyscallName: "getpgrp", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	66: SyscallMeta{SyscallName: "setsid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	67: SyscallMeta{SyscallName: "sigaction", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct old_sigaction __user *"},
		{KernelType: "struct old_sigaction __user *"},
	}},
	68: SyscallMeta{SyscallName: "sgetmask", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	69: SyscallMeta{SyscallName: "ssetmask", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	70: SyscallMeta{SyscallName: "setreuid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
	}},
	71: SyscallMeta{SyscallName: "setregid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
	}},
	72: SyscallMeta{SyscallName: "sigsuspend", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "old_sigset_t"},
		{KernelType: ""},
		{KernelType: ""},
	}},
	73: SyscallMeta{SyscallName: "sigpending", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "old_sigset_t __user *"},
	}},
	74: SyscallMeta{SyscallName: "sethostname", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	75: SyscallMeta{SyscallName: "setrlimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit __user *"},
	}},
	76: SyscallMeta{SyscallName: "getrlimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit __user *"},
	}},
	77: SyscallMeta{SyscallName: "getrusage", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	78: SyscallMeta{SyscallName: "gettimeofday", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_timeval __user *"},
		{KernelType: "struct timezone __user *"},
	}},
	79: SyscallMeta{SyscallName: "settimeofday", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_timeval __user *"},
		{KernelType: "struct timezone __user *"},
	}},
	80: SyscallMeta{SyscallName: "getgroups", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "gid_t __user *"},
	}},
	81: SyscallMeta{SyscallName: "setgroups", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "gid_t __user *"},
	}},
	82: SyscallMeta{SyscallName: "select", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	83: SyscallMeta{SyscallName: "symlink", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	84: SyscallMeta{SyscallName: "oldlstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	85: SyscallMeta{SyscallName: "readlink", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	86: SyscallMeta{SyscallName: "uselib", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	87: SyscallMeta{SyscallName: "swapon", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	88: SyscallMeta{SyscallName: "reboot", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "void __user *"},
	}},
	89: SyscallMeta{SyscallName: "readdir", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	90: SyscallMeta{SyscallName: "mmap", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
	}},
	91: SyscallMeta{SyscallName: "munmap", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	92: SyscallMeta{SyscallName: "truncate", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "long"},
	}},
	93: SyscallMeta{SyscallName: "ftruncate", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	94: SyscallMeta{SyscallName: "fchmod", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "umode_t"},
	}},
	95: SyscallMeta{SyscallName: "fchown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	96: SyscallMeta{SyscallName: "getpriority", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	97: SyscallMeta{SyscallName: "setpriority", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	98: SyscallMeta{SyscallName: "profil", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	99: SyscallMeta{SyscallName: "statfs", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct statfs __user *"},
	}},
	100: SyscallMeta{SyscallName: "fstatfs", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct statfs __user *"},
	}},
	101: SyscallMeta{SyscallName: "ioperm", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "int"},
	}},
	102: SyscallMeta{SyscallName: "socketcall", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "u32 __user *"},
	}},
	103: SyscallMeta{SyscallName: "syslog", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	104: SyscallMeta{SyscallName: "setitimer", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct old_itimerval __user *"},
		{KernelType: "struct old_itimerval __user *"},
	}},
	105: SyscallMeta{SyscallName: "getitimer", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct old_itimerval __user *"},
	}},
	106: SyscallMeta{SyscallName: "stat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	107: SyscallMeta{SyscallName: "lstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	108: SyscallMeta{SyscallName: "fstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	109: SyscallMeta{SyscallName: "olduname", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct oldold_utsname __user *"},
	}},
	110: SyscallMeta{SyscallName: "iopl", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	111: SyscallMeta{SyscallName: "vhangup", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	112: SyscallMeta{SyscallName: "idle", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	113: SyscallMeta{SyscallName: "vm86old", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct vm86_struct __user *"},
	}},
	114: SyscallMeta{SyscallName: "wait4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "uint_t __user *"},
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	115: SyscallMeta{SyscallName: "swapoff", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	116: SyscallMeta{SyscallName: "sysinfo", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct sysinfo __user *"},
	}},
	117: SyscallMeta{SyscallName: "ipc", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "uptr_t"},
		{KernelType: "unsigned int"},
	}},
	118: SyscallMeta{SyscallName: "fsync", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	119: SyscallMeta{SyscallName: "sigreturn", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	120: SyscallMeta{SyscallName: "clone", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "int __user *"},
		{KernelType: "int __user *"},
		{KernelType: "unsigned long"},
	}},
	121: SyscallMeta{SyscallName: "setdomainname", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	122: SyscallMeta{SyscallName: "uname", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_utsname __user *"},
	}},
	123: SyscallMeta{SyscallName: "modify_ldt", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "unsigned long"},
	}},
	124: SyscallMeta{SyscallName: "adjtimex", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct timex __user *"},
	}},
	125: SyscallMeta{SyscallName: "mprotect", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned long"},
	}},
	126: SyscallMeta{SyscallName: "sigprocmask", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "old_sigset_t __user *"},
		{KernelType: "old_sigset_t __user *"},
	}},
	127: SyscallMeta{SyscallName: "create_module", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	128: SyscallMeta{SyscallName: "init_module", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "void __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "char __user *"},
	}},
	129: SyscallMeta{SyscallName: "delete_module", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	130: SyscallMeta{SyscallName: "get_kernel_syms", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	131: SyscallMeta{SyscallName: "quotactl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "qid_t"},
		{KernelType: "void __user *"},
	}},
	132: SyscallMeta{SyscallName: "getpgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	133: SyscallMeta{SyscallName: "fchdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	134: SyscallMeta{SyscallName: "bdflush", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "long"},
	}},
	135: SyscallMeta{SyscallName: "sysfs", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	136: SyscallMeta{SyscallName: "personality", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	137: SyscallMeta{SyscallName: "afs_syscall", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	138: SyscallMeta{SyscallName: "setfsuid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
	}},
	139: SyscallMeta{SyscallName: "setfsgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
	}},
	140: SyscallMeta{SyscallName: "_llseek", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	141: SyscallMeta{SyscallName: "getdents", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct linux_dirent __user *"},
		{KernelType: "unsigned int"},
	}},
	142: SyscallMeta{SyscallName: "_newselect", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	143: SyscallMeta{SyscallName: "flock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	144: SyscallMeta{SyscallName: "msync", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	145: SyscallMeta{SyscallName: "readv", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
	}},
	146: SyscallMeta{SyscallName: "writev", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
	}},
	147: SyscallMeta{SyscallName: "getsid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	148: SyscallMeta{SyscallName: "fdatasync", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	149: SyscallMeta{SyscallName: "_sysctl", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	150: SyscallMeta{SyscallName: "mlock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	151: SyscallMeta{SyscallName: "munlock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	152: SyscallMeta{SyscallName: "mlockall", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	153: SyscallMeta{SyscallName: "munlockall", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	154: SyscallMeta{SyscallName: "sched_setparam", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_param __user *"},
	}},
	155: SyscallMeta{SyscallName: "sched_getparam", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_param __user *"},
	}},
	156: SyscallMeta{SyscallName: "sched_setscheduler", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "struct sched_param __user *"},
	}},
	157: SyscallMeta{SyscallName: "sched_getscheduler", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	158: SyscallMeta{SyscallName: "sched_yield", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	159: SyscallMeta{SyscallName: "sched_get_priority_max", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	160: SyscallMeta{SyscallName: "sched_get_priority_min", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	161: SyscallMeta{SyscallName: "sched_rr_get_interval", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	162: SyscallMeta{SyscallName: "nanosleep", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	163: SyscallMeta{SyscallName: "mremap", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	164: SyscallMeta{SyscallName: "setresuid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
	}},
	165: SyscallMeta{SyscallName: "getresuid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t __user *"},
		{KernelType: "uid_t __user *"},
		{KernelType: "uid_t __user *"},
	}},
	166: SyscallMeta{SyscallName: "vm86", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	167: SyscallMeta{SyscallName: "query_module", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	168: SyscallMeta{SyscallName: "poll", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct pollfd __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	169: SyscallMeta{SyscallName: "nfsservctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	170: SyscallMeta{SyscallName: "setresgid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
	}},
	171: SyscallMeta{SyscallName: "getresgid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t __user *"},
		{KernelType: "gid_t __user *"},
		{KernelType: "gid_t __user *"},
	}},
	172: SyscallMeta{SyscallName: "prctl", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	173: SyscallMeta{SyscallName: "rt_sigreturn", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	174: SyscallMeta{SyscallName: "rt_sigaction", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sigaction __user *"},
		{KernelType: "struct sigaction __user *"},
		{KernelType: "size_t"},
	}},
	175: SyscallMeta{SyscallName: "rt_sigprocmask", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	176: SyscallMeta{SyscallName: "rt_sigpending", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	177: SyscallMeta{SyscallName: "rt_sigtimedwait", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "siginfo_t __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "size_t"},
	}},
	178: SyscallMeta{SyscallName: "rt_sigqueueinfo", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "siginfo_t __user *"},
	}},
	179: SyscallMeta{SyscallName: "rt_sigsuspend", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	180: SyscallMeta{SyscallName: "pread64", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "loff_t"},
		{KernelType: ""},
	}},
	181: SyscallMeta{SyscallName: "pwrite64", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "loff_t"},
		{KernelType: ""},
	}},
	182: SyscallMeta{SyscallName: "chown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	183: SyscallMeta{SyscallName: "getcwd", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned long"},
	}},
	184: SyscallMeta{SyscallName: "capget", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "cap_user_header_t"},
		{KernelType: "cap_user_data_t"},
	}},
	185: SyscallMeta{SyscallName: "capset", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "cap_user_header_t"},
		{KernelType: "cap_user_data_t"},
	}},
	186: SyscallMeta{SyscallName: "sigaltstack", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "stack_t __user *"},
		{KernelType: "stack_t __user *"},
	}},
	187: SyscallMeta{SyscallName: "sendfile", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "off_t __user *"},
		{KernelType: "size_t"},
	}},
	188: SyscallMeta{SyscallName: "getpmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	189: SyscallMeta{SyscallName: "putpmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	190: SyscallMeta{SyscallName: "vfork", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	191: SyscallMeta{SyscallName: "ugetrlimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	192: SyscallMeta{SyscallName: "mmap2", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	193: SyscallMeta{SyscallName: "truncate64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "loff_t"},
		{KernelType: ""},
	}},
	194: SyscallMeta{SyscallName: "ftruncate64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "loff_t"},
		{KernelType: ""},
	}},
	195: SyscallMeta{SyscallName: "stat64", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct stat64 __user *"},
	}},
	196: SyscallMeta{SyscallName: "lstat64", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct stat64 __user *"},
	}},
	197: SyscallMeta{SyscallName: "fstat64", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct stat64 __user *"},
	}},
	198: SyscallMeta{SyscallName: "lchown32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	199: SyscallMeta{SyscallName: "getuid32", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	200: SyscallMeta{SyscallName: "getgid32", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	201: SyscallMeta{SyscallName: "geteuid32", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	202: SyscallMeta{SyscallName: "getegid32", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	203: SyscallMeta{SyscallName: "setreuid32", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	204: SyscallMeta{SyscallName: "setregid32", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	205: SyscallMeta{SyscallName: "getgroups32", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	206: SyscallMeta{SyscallName: "setgroups32", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	207: SyscallMeta{SyscallName: "fchown32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	208: SyscallMeta{SyscallName: "setresuid32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	209: SyscallMeta{SyscallName: "getresuid32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	210: SyscallMeta{SyscallName: "setresgid32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	211: SyscallMeta{SyscallName: "getresgid32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	212: SyscallMeta{SyscallName: "chown32", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	213: SyscallMeta{SyscallName: "setuid32", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	214: SyscallMeta{SyscallName: "setgid32", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	215: SyscallMeta{SyscallName: "setfsuid32", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	216: SyscallMeta{SyscallName: "setfsgid32", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	217: SyscallMeta{SyscallName: "pivot_root", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	218: SyscallMeta{SyscallName: "mincore", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned char __user *"},
	}},
	219: SyscallMeta{SyscallName: "madvise", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	220: SyscallMeta{SyscallName: "getdents64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct linux_dirent64 __user *"},
		{KernelType: "unsigned int"},
	}},
	221: SyscallMeta{SyscallName: "fcntl64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	224: SyscallMeta{SyscallName: "gettid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	225: SyscallMeta{SyscallName: "readahead", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "size_t"},
		{KernelType: ""},
	}},
	226: SyscallMeta{SyscallName: "setxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	227: SyscallMeta{SyscallName: "lsetxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	228: SyscallMeta{SyscallName: "fsetxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	229: SyscallMeta{SyscallName: "getxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	230: SyscallMeta{SyscallName: "lgetxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	231: SyscallMeta{SyscallName: "fgetxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	232: SyscallMeta{SyscallName: "listxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	233: SyscallMeta{SyscallName: "llistxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	234: SyscallMeta{SyscallName: "flistxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	235: SyscallMeta{SyscallName: "removexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	236: SyscallMeta{SyscallName: "lremovexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	237: SyscallMeta{SyscallName: "fremovexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	238: SyscallMeta{SyscallName: "tkill", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	239: SyscallMeta{SyscallName: "sendfile64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "size_t"},
	}},
	240: SyscallMeta{SyscallName: "futex", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "u32 __user *"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "u32 __user *"},
		{KernelType: "unsigned int"},
	}},
	241: SyscallMeta{SyscallName: "sched_setaffinity", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long __user *"},
	}},
	242: SyscallMeta{SyscallName: "sched_getaffinity", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long __user *"},
	}},
	243: SyscallMeta{SyscallName: "set_thread_area", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct user_desc __user *"},
	}},
	244: SyscallMeta{SyscallName: "get_thread_area", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct user_desc __user *"},
	}},
	245: SyscallMeta{SyscallName: "io_setup", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned"},
		{KernelType: "aio_context_t __user *"},
	}},
	246: SyscallMeta{SyscallName: "io_destroy", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
	}},
	247: SyscallMeta{SyscallName: "io_getevents", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "struct io_event __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	248: SyscallMeta{SyscallName: "io_submit", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "int"},
		{KernelType: "uptr_t __user *"},
	}},
	249: SyscallMeta{SyscallName: "io_cancel", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "struct iocb __user *"},
		{KernelType: "struct io_event __user *"},
	}},
	250: SyscallMeta{SyscallName: "fadvise64", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "size_t"},
		{KernelType: "int"},
		{KernelType: ""},
	}},
	252: SyscallMeta{SyscallName: "exit_group", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	253: SyscallMeta{SyscallName: "lookup_dcookie", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "u64"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: ""},
	}},
	254: SyscallMeta{SyscallName: "epoll_create", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	255: SyscallMeta{SyscallName: "epoll_ctl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
	}},
	256: SyscallMeta{SyscallName: "epoll_wait", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	257: SyscallMeta{SyscallName: "remap_file_pages", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	258: SyscallMeta{SyscallName: "set_tid_address", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
	}},
	259: SyscallMeta{SyscallName: "timer_create", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct sigevent __user *"},
		{KernelType: "timer_t __user *"},
	}},
	260: SyscallMeta{SyscallName: "timer_settime", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
		{KernelType: "struct itimerspec __user *"},
	}},
	261: SyscallMeta{SyscallName: "timer_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
		{KernelType: "struct itimerspec __user *"},
	}},
	262: SyscallMeta{SyscallName: "timer_getoverrun", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
	}},
	263: SyscallMeta{SyscallName: "timer_delete", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
	}},
	264: SyscallMeta{SyscallName: "clock_settime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	265: SyscallMeta{SyscallName: "clock_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	266: SyscallMeta{SyscallName: "clock_getres", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	267: SyscallMeta{SyscallName: "clock_nanosleep", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	268: SyscallMeta{SyscallName: "statfs64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "struct statfs64 __user *"},
	}},
	269: SyscallMeta{SyscallName: "fstatfs64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "size_t"},
		{KernelType: "struct statfs64 __user *"},
	}},
	270: SyscallMeta{SyscallName: "tgkill", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	271: SyscallMeta{SyscallName: "utimes", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct old_timeval __user *"},
	}},
	272: SyscallMeta{SyscallName: "fadvise64_64", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "loff_t"},
		{KernelType: "int"},
		{KernelType: ""},
		{KernelType: ""},
	}},
	273: SyscallMeta{SyscallName: "vserver", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	274: SyscallMeta{SyscallName: "mbind", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	275: SyscallMeta{SyscallName: "get_mempolicy", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	276: SyscallMeta{SyscallName: "set_mempolicy", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
	}},
	277: SyscallMeta{SyscallName: "mq_open", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "mode_t"},
		{KernelType: "struct mq_attr __user *"},
	}},
	278: SyscallMeta{SyscallName: "mq_unlink", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	279: SyscallMeta{SyscallName: "mq_timedsend", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
	}},
	280: SyscallMeta{SyscallName: "mq_timedreceive", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	281: SyscallMeta{SyscallName: "mq_notify", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "struct sigevent __user *"},
	}},
	282: SyscallMeta{SyscallName: "mq_getsetattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "struct mq_attr __user *"},
		{KernelType: "struct mq_attr __user *"},
	}},
	283: SyscallMeta{SyscallName: "kexec_load", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "struct kexec_segment __user *"},
		{KernelType: "unsigned long"},
	}},
	284: SyscallMeta{SyscallName: "waitid", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "pid_t"},
		{KernelType: "struct siginfo __user *"},
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	286: SyscallMeta{SyscallName: "add_key", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "key_serial_t"},
	}},
	287: SyscallMeta{SyscallName: "request_key", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "key_serial_t"},
	}},
	288: SyscallMeta{SyscallName: "keyctl", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	289: SyscallMeta{SyscallName: "ioprio_set", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	290: SyscallMeta{SyscallName: "ioprio_get", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	291: SyscallMeta{SyscallName: "inotify_init", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	292: SyscallMeta{SyscallName: "inotify_add_watch", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	293: SyscallMeta{SyscallName: "inotify_rm_watch", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "__s32"},
	}},
	294: SyscallMeta{SyscallName: "migrate_pages", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long __user *"},
	}},
	295: SyscallMeta{SyscallName: "openat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "umode_t"},
	}},
	296: SyscallMeta{SyscallName: "mkdirat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	297: SyscallMeta{SyscallName: "mknodat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
		{KernelType: "unsigned int"},
	}},
	298: SyscallMeta{SyscallName: "fchownat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
		{KernelType: "int"},
	}},
	299: SyscallMeta{SyscallName: "futimesat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct old_timeval __user *"},
	}},
	300: SyscallMeta{SyscallName: "fstatat64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct stat64 __user *"},
		{KernelType: "int"},
	}},
	301: SyscallMeta{SyscallName: "unlinkat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	302: SyscallMeta{SyscallName: "renameat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	303: SyscallMeta{SyscallName: "linkat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	304: SyscallMeta{SyscallName: "symlinkat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	305: SyscallMeta{SyscallName: "readlinkat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	306: SyscallMeta{SyscallName: "fchmodat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	307: SyscallMeta{SyscallName: "faccessat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	308: SyscallMeta{SyscallName: "pselect6", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "void __user *"},
	}},
	309: SyscallMeta{SyscallName: "ppoll", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct pollfd __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	310: SyscallMeta{SyscallName: "unshare", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
	}},
	311: SyscallMeta{SyscallName: "set_robust_list", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct robust_list_head __user *"},
		{KernelType: "size_t"},
	}},
	312: SyscallMeta{SyscallName: "get_robust_list", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct robust_list_head __user * __user *"},
		{KernelType: "size_t __user *"},
	}},
	313: SyscallMeta{SyscallName: "splice", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	314: SyscallMeta{SyscallName: "sync_file_range", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "loff_t"},
		{KernelType: "unsigned int"},
		{KernelType: ""},
		{KernelType: ""},
	}},
	315: SyscallMeta{SyscallName: "tee", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	316: SyscallMeta{SyscallName: "vmsplice", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	317: SyscallMeta{SyscallName: "move_pages", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned long"},
		{KernelType: "uptr_t __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	318: SyscallMeta{SyscallName: "getcpu", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned __user *"},
		{KernelType: "unsigned __user *"},
		{KernelType: "struct getcpu_cache __user *"},
	}},
	319: SyscallMeta{SyscallName: "epoll_pwait", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	320: SyscallMeta{SyscallName: "utimensat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "int"},
	}},
	321: SyscallMeta{SyscallName: "signalfd", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	322: SyscallMeta{SyscallName: "timerfd_create", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	323: SyscallMeta{SyscallName: "eventfd", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	324: SyscallMeta{SyscallName: "fallocate", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "loff_t"},
		{KernelType: ""},
		{KernelType: ""},
	}},
	325: SyscallMeta{SyscallName: "timerfd_settime", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
		{KernelType: "struct itimerspec __user *"},
	}},
	326: SyscallMeta{SyscallName: "timerfd_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
	}},
	327: SyscallMeta{SyscallName: "signalfd4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	328: SyscallMeta{SyscallName: "eventfd2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	329: SyscallMeta{SyscallName: "epoll_create1", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	330: SyscallMeta{SyscallName: "dup3", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	331: SyscallMeta{SyscallName: "pipe2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	332: SyscallMeta{SyscallName: "inotify_init1", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	333: SyscallMeta{SyscallName: "preadv", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	334: SyscallMeta{SyscallName: "pwritev", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	335: SyscallMeta{SyscallName: "rt_tgsigqueueinfo", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "siginfo_t __user *"},
	}},
	336: SyscallMeta{SyscallName: "perf_event_open", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct perf_event_attr __user *"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned long"},
	}},
	337: SyscallMeta{SyscallName: "recvmmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct mmsghdr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
	}},
	338: SyscallMeta{SyscallName: "fanotify_init", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	339: SyscallMeta{SyscallName: "fanotify_mark", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "__u64"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: ""},
	}},
	340: SyscallMeta{SyscallName: "prlimit64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit64 __user *"},
		{KernelType: "struct rlimit64 __user *"},
	}},
	341: SyscallMeta{SyscallName: "name_to_handle_at", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct file_handle __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	342: SyscallMeta{SyscallName: "open_by_handle_at", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct file_handle __user *"},
		{KernelType: "int"},
	}},
	343: SyscallMeta{SyscallName: "clock_adjtime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timex __user *"},
	}},
	344: SyscallMeta{SyscallName: "syncfs", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	345: SyscallMeta{SyscallName: "sendmmsg", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct mmsghdr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	346: SyscallMeta{SyscallName: "setns", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	347: SyscallMeta{SyscallName: "process_vm_readv", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	348: SyscallMeta{SyscallName: "process_vm_writev", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	349: SyscallMeta{SyscallName: "kcmp", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	350: SyscallMeta{SyscallName: "finit_module", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	351: SyscallMeta{SyscallName: "sched_setattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_attr __user *"},
		{KernelType: "unsigned int"},
	}},
	352: SyscallMeta{SyscallName: "sched_getattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_attr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	353: SyscallMeta{SyscallName: "renameat2", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	354: SyscallMeta{SyscallName: "seccomp", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "void __user *"},
	}},
	355: SyscallMeta{SyscallName: "getrandom", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	356: SyscallMeta{SyscallName: "memfd_create", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	357: SyscallMeta{SyscallName: "bpf", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "union bpf_attr __user *"},
		{KernelType: "unsigned int"},
	}},
	358: SyscallMeta{SyscallName: "execveat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "int"},
	}},
	359: SyscallMeta{SyscallName: "socket", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	360: SyscallMeta{SyscallName: "socketpair", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int __user *"},
	}},
	361: SyscallMeta{SyscallName: "bind", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	362: SyscallMeta{SyscallName: "connect", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	363: SyscallMeta{SyscallName: "listen", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	364: SyscallMeta{SyscallName: "accept4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	365: SyscallMeta{SyscallName: "getsockopt", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int __user *"},
	}},
	366: SyscallMeta{SyscallName: "setsockopt", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	367: SyscallMeta{SyscallName: "getsockname", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	368: SyscallMeta{SyscallName: "getpeername", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	369: SyscallMeta{SyscallName: "sendto", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	370: SyscallMeta{SyscallName: "sendmsg", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msghdr __user *"},
		{KernelType: "unsigned int"},
	}},
	371: SyscallMeta{SyscallName: "recvfrom", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	372: SyscallMeta{SyscallName: "recvmsg", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msghdr __user *"},
		{KernelType: "unsigned int"},
	}},
	373: SyscallMeta{SyscallName: "shutdown", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	374: SyscallMeta{SyscallName: "userfaultfd", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	375: SyscallMeta{SyscallName: "membarrier", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	376: SyscallMeta{SyscallName: "mlock2", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	377: SyscallMeta{SyscallName: "copy_file_range", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	378: SyscallMeta{SyscallName: "preadv2", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "rwf_t"},
	}},
	379: SyscallMeta{SyscallName: "pwritev2", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "rwf_t"},
	}},
	380: SyscallMeta{SyscallName: "pkey_mprotect", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned long"},
		{KernelType: "int"},
	}},
	381: SyscallMeta{SyscallName: "pkey_alloc", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	382: SyscallMeta{SyscallName: "pkey_free", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	383: SyscallMeta{SyscallName: "statx", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned"},
		{KernelType: "unsigned int"},
		{KernelType: "struct statx __user *"},
	}},
	384: SyscallMeta{SyscallName: "arch_prctl", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
	}},
	385: SyscallMeta{SyscallName: "io_pgetevents", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "struct io_event __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct __aio_sigset __user *"},
	}},
	386: SyscallMeta{SyscallName: "rseq", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct rseq __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
	}},
	393: SyscallMeta{SyscallName: "semget", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	394: SyscallMeta{SyscallName: "semctl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	395: SyscallMeta{SyscallName: "shmget", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	396: SyscallMeta{SyscallName: "shmctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct shmid_ds __user *"},
	}},
	397: SyscallMeta{SyscallName: "shmat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	398: SyscallMeta{SyscallName: "shmdt", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	399: SyscallMeta{SyscallName: "msgget", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "int"},
	}},
	400: SyscallMeta{SyscallName: "msgsnd", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msgbuf __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	401: SyscallMeta{SyscallName: "msgrcv", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msgbuf __user *"},
		{KernelType: "size_t"},
		{KernelType: "long"},
		{KernelType: "int"},
	}},
	402: SyscallMeta{SyscallName: "msgctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct msqid_ds __user *"},
	}},
}
