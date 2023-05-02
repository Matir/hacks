package ptrace

var SyscallMetadata = map[int]SyscallMeta{
	0: SyscallMeta{SyscallName: "read", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	1: SyscallMeta{SyscallName: "write", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	2: SyscallMeta{SyscallName: "open", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "umode_t"},
	}},
	3: SyscallMeta{SyscallName: "close", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	4: SyscallMeta{SyscallName: "stat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	5: SyscallMeta{SyscallName: "fstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	6: SyscallMeta{SyscallName: "lstat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct __old_kernel_stat __user *"},
	}},
	7: SyscallMeta{SyscallName: "poll", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct pollfd __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	8: SyscallMeta{SyscallName: "lseek", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "off_t"},
		{KernelType: "unsigned int"},
	}},
	9: SyscallMeta{SyscallName: "mmap", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	10: SyscallMeta{SyscallName: "mprotect", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned long"},
	}},
	11: SyscallMeta{SyscallName: "munmap", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	12: SyscallMeta{SyscallName: "brk", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
	}},
	13: SyscallMeta{SyscallName: "rt_sigaction", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sigaction __user *"},
		{KernelType: "struct sigaction __user *"},
		{KernelType: "size_t"},
	}},
	14: SyscallMeta{SyscallName: "rt_sigprocmask", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	15: SyscallMeta{SyscallName: "rt_sigreturn", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	16: SyscallMeta{SyscallName: "ioctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	17: SyscallMeta{SyscallName: "pread64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "loff_t"},
	}},
	18: SyscallMeta{SyscallName: "pwrite64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "loff_t"},
	}},
	19: SyscallMeta{SyscallName: "readv", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
	}},
	20: SyscallMeta{SyscallName: "writev", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
	}},
	21: SyscallMeta{SyscallName: "access", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	22: SyscallMeta{SyscallName: "pipe", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
	}},
	23: SyscallMeta{SyscallName: "select", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "struct old_timeval __user *"},
	}},
	24: SyscallMeta{SyscallName: "sched_yield", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	25: SyscallMeta{SyscallName: "mremap", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	26: SyscallMeta{SyscallName: "msync", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	27: SyscallMeta{SyscallName: "mincore", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned char __user *"},
	}},
	28: SyscallMeta{SyscallName: "madvise", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	29: SyscallMeta{SyscallName: "shmget", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	30: SyscallMeta{SyscallName: "shmat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	31: SyscallMeta{SyscallName: "shmctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct shmid_ds __user *"},
	}},
	32: SyscallMeta{SyscallName: "dup", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	33: SyscallMeta{SyscallName: "dup2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	34: SyscallMeta{SyscallName: "pause", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	35: SyscallMeta{SyscallName: "nanosleep", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	36: SyscallMeta{SyscallName: "getitimer", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct old_itimerval __user *"},
	}},
	37: SyscallMeta{SyscallName: "alarm", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	38: SyscallMeta{SyscallName: "setitimer", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct old_itimerval __user *"},
		{KernelType: "struct old_itimerval __user *"},
	}},
	39: SyscallMeta{SyscallName: "getpid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	40: SyscallMeta{SyscallName: "sendfile", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "off_t __user *"},
		{KernelType: "size_t"},
	}},
	41: SyscallMeta{SyscallName: "socket", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	42: SyscallMeta{SyscallName: "connect", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	43: SyscallMeta{SyscallName: "accept", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	44: SyscallMeta{SyscallName: "sendto", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	45: SyscallMeta{SyscallName: "recvfrom", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	46: SyscallMeta{SyscallName: "sendmsg", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msghdr __user *"},
		{KernelType: "unsigned int"},
	}},
	47: SyscallMeta{SyscallName: "recvmsg", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msghdr __user *"},
		{KernelType: "unsigned int"},
	}},
	48: SyscallMeta{SyscallName: "shutdown", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	49: SyscallMeta{SyscallName: "bind", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int"},
	}},
	50: SyscallMeta{SyscallName: "listen", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	51: SyscallMeta{SyscallName: "getsockname", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	52: SyscallMeta{SyscallName: "getpeername", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
	}},
	53: SyscallMeta{SyscallName: "socketpair", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int __user *"},
	}},
	54: SyscallMeta{SyscallName: "setsockopt", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	55: SyscallMeta{SyscallName: "getsockopt", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int __user *"},
	}},
	56: SyscallMeta{SyscallName: "clone", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "int __user *"},
		{KernelType: "int __user *"},
		{KernelType: "unsigned long"},
	}},
	57: SyscallMeta{SyscallName: "fork", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	58: SyscallMeta{SyscallName: "vfork", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	59: SyscallMeta{SyscallName: "execve", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "char __user * __user *"},
	}},
	60: SyscallMeta{SyscallName: "exit", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	61: SyscallMeta{SyscallName: "wait4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "uint_t __user *"},
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	62: SyscallMeta{SyscallName: "kill", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	63: SyscallMeta{SyscallName: "uname", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_utsname __user *"},
	}},
	64: SyscallMeta{SyscallName: "semget", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	65: SyscallMeta{SyscallName: "semop", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sembuf __user *"},
		{KernelType: "unsigned"},
	}},
	66: SyscallMeta{SyscallName: "semctl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	67: SyscallMeta{SyscallName: "shmdt", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	68: SyscallMeta{SyscallName: "msgget", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "key_t"},
		{KernelType: "int"},
	}},
	69: SyscallMeta{SyscallName: "msgsnd", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msgbuf __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	70: SyscallMeta{SyscallName: "msgrcv", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct msgbuf __user *"},
		{KernelType: "size_t"},
		{KernelType: "long"},
		{KernelType: "int"},
	}},
	71: SyscallMeta{SyscallName: "msgctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct msqid_ds __user *"},
	}},
	72: SyscallMeta{SyscallName: "fcntl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	73: SyscallMeta{SyscallName: "flock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	74: SyscallMeta{SyscallName: "fsync", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	75: SyscallMeta{SyscallName: "fdatasync", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	76: SyscallMeta{SyscallName: "truncate", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "long"},
	}},
	77: SyscallMeta{SyscallName: "ftruncate", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long"},
	}},
	78: SyscallMeta{SyscallName: "getdents", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct linux_dirent __user *"},
		{KernelType: "unsigned int"},
	}},
	79: SyscallMeta{SyscallName: "getcwd", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned long"},
	}},
	80: SyscallMeta{SyscallName: "chdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	81: SyscallMeta{SyscallName: "fchdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	82: SyscallMeta{SyscallName: "rename", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	83: SyscallMeta{SyscallName: "mkdir", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	84: SyscallMeta{SyscallName: "rmdir", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	85: SyscallMeta{SyscallName: "creat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	86: SyscallMeta{SyscallName: "link", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	87: SyscallMeta{SyscallName: "unlink", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	88: SyscallMeta{SyscallName: "symlink", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	89: SyscallMeta{SyscallName: "readlink", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	90: SyscallMeta{SyscallName: "chmod", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	91: SyscallMeta{SyscallName: "fchmod", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "umode_t"},
	}},
	92: SyscallMeta{SyscallName: "chown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	93: SyscallMeta{SyscallName: "fchown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	94: SyscallMeta{SyscallName: "lchown", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
	}},
	95: SyscallMeta{SyscallName: "umask", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	96: SyscallMeta{SyscallName: "gettimeofday", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_timeval __user *"},
		{KernelType: "struct timezone __user *"},
	}},
	97: SyscallMeta{SyscallName: "getrlimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit __user *"},
	}},
	98: SyscallMeta{SyscallName: "getrusage", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	99: SyscallMeta{SyscallName: "sysinfo", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct sysinfo __user *"},
	}},
	100: SyscallMeta{SyscallName: "times", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct tms __user *"},
	}},
	101: SyscallMeta{SyscallName: "ptrace", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	102: SyscallMeta{SyscallName: "getuid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	103: SyscallMeta{SyscallName: "syslog", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	104: SyscallMeta{SyscallName: "getgid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	105: SyscallMeta{SyscallName: "setuid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
	}},
	106: SyscallMeta{SyscallName: "setgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
	}},
	107: SyscallMeta{SyscallName: "geteuid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	108: SyscallMeta{SyscallName: "getegid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	109: SyscallMeta{SyscallName: "setpgid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
	}},
	110: SyscallMeta{SyscallName: "getppid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	111: SyscallMeta{SyscallName: "getpgrp", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	112: SyscallMeta{SyscallName: "setsid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	113: SyscallMeta{SyscallName: "setreuid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
	}},
	114: SyscallMeta{SyscallName: "setregid", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
	}},
	115: SyscallMeta{SyscallName: "getgroups", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "gid_t __user *"},
	}},
	116: SyscallMeta{SyscallName: "setgroups", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "gid_t __user *"},
	}},
	117: SyscallMeta{SyscallName: "setresuid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
		{KernelType: "uid_t"},
	}},
	118: SyscallMeta{SyscallName: "getresuid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t __user *"},
		{KernelType: "uid_t __user *"},
		{KernelType: "uid_t __user *"},
	}},
	119: SyscallMeta{SyscallName: "setresgid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
		{KernelType: "gid_t"},
	}},
	120: SyscallMeta{SyscallName: "getresgid", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t __user *"},
		{KernelType: "gid_t __user *"},
		{KernelType: "gid_t __user *"},
	}},
	121: SyscallMeta{SyscallName: "getpgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	122: SyscallMeta{SyscallName: "setfsuid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "uid_t"},
	}},
	123: SyscallMeta{SyscallName: "setfsgid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "gid_t"},
	}},
	124: SyscallMeta{SyscallName: "getsid", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	125: SyscallMeta{SyscallName: "capget", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "cap_user_header_t"},
		{KernelType: "cap_user_data_t"},
	}},
	126: SyscallMeta{SyscallName: "capset", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "cap_user_header_t"},
		{KernelType: "cap_user_data_t"},
	}},
	127: SyscallMeta{SyscallName: "rt_sigpending", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	128: SyscallMeta{SyscallName: "rt_sigtimedwait", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "siginfo_t __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "size_t"},
	}},
	129: SyscallMeta{SyscallName: "rt_sigqueueinfo", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "siginfo_t __user *"},
	}},
	130: SyscallMeta{SyscallName: "rt_sigsuspend", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	131: SyscallMeta{SyscallName: "sigaltstack", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "stack_t __user *"},
		{KernelType: "stack_t __user *"},
	}},
	132: SyscallMeta{SyscallName: "utime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct utimbuf __user *"},
	}},
	133: SyscallMeta{SyscallName: "mknod", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
		{KernelType: "unsigned"},
	}},
	134: SyscallMeta{SyscallName: "uselib", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	135: SyscallMeta{SyscallName: "personality", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	136: SyscallMeta{SyscallName: "ustat", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned"},
		{KernelType: "struct ustat __user *"},
	}},
	137: SyscallMeta{SyscallName: "statfs", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct statfs __user *"},
	}},
	138: SyscallMeta{SyscallName: "fstatfs", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct statfs __user *"},
	}},
	139: SyscallMeta{SyscallName: "sysfs", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	140: SyscallMeta{SyscallName: "getpriority", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	141: SyscallMeta{SyscallName: "setpriority", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	142: SyscallMeta{SyscallName: "sched_setparam", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_param __user *"},
	}},
	143: SyscallMeta{SyscallName: "sched_getparam", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_param __user *"},
	}},
	144: SyscallMeta{SyscallName: "sched_setscheduler", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "struct sched_param __user *"},
	}},
	145: SyscallMeta{SyscallName: "sched_getscheduler", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
	}},
	146: SyscallMeta{SyscallName: "sched_get_priority_max", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	147: SyscallMeta{SyscallName: "sched_get_priority_min", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	148: SyscallMeta{SyscallName: "sched_rr_get_interval", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	149: SyscallMeta{SyscallName: "mlock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	150: SyscallMeta{SyscallName: "munlock", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
	}},
	151: SyscallMeta{SyscallName: "mlockall", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	152: SyscallMeta{SyscallName: "munlockall", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	153: SyscallMeta{SyscallName: "vhangup", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	154: SyscallMeta{SyscallName: "modify_ldt", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "void __user *"},
		{KernelType: "unsigned long"},
	}},
	155: SyscallMeta{SyscallName: "pivot_root", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	156: SyscallMeta{SyscallName: "_sysctl", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	157: SyscallMeta{SyscallName: "prctl", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	158: SyscallMeta{SyscallName: "arch_prctl", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
	}},
	159: SyscallMeta{SyscallName: "adjtimex", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct timex __user *"},
	}},
	160: SyscallMeta{SyscallName: "setrlimit", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit __user *"},
	}},
	161: SyscallMeta{SyscallName: "chroot", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	162: SyscallMeta{SyscallName: "sync", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	163: SyscallMeta{SyscallName: "acct", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	164: SyscallMeta{SyscallName: "settimeofday", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct old_timeval __user *"},
		{KernelType: "struct timezone __user *"},
	}},
	165: SyscallMeta{SyscallName: "mount", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "void __user *"},
	}},
	166: SyscallMeta{SyscallName: "umount2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	167: SyscallMeta{SyscallName: "swapon", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	168: SyscallMeta{SyscallName: "swapoff", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	169: SyscallMeta{SyscallName: "reboot", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "void __user *"},
	}},
	170: SyscallMeta{SyscallName: "sethostname", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	171: SyscallMeta{SyscallName: "setdomainname", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	172: SyscallMeta{SyscallName: "iopl", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	173: SyscallMeta{SyscallName: "ioperm", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "int"},
	}},
	174: SyscallMeta{SyscallName: "create_module", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
	}},
	175: SyscallMeta{SyscallName: "init_module", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "void __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "char __user *"},
	}},
	176: SyscallMeta{SyscallName: "delete_module", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	177: SyscallMeta{SyscallName: "get_kernel_syms", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
	}},
	178: SyscallMeta{SyscallName: "query_module", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	179: SyscallMeta{SyscallName: "quotactl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "char __user *"},
		{KernelType: "qid_t"},
		{KernelType: "void __user *"},
	}},
	180: SyscallMeta{SyscallName: "nfsservctl", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	181: SyscallMeta{SyscallName: "getpmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	182: SyscallMeta{SyscallName: "putpmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	183: SyscallMeta{SyscallName: "afs_syscall", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	184: SyscallMeta{SyscallName: "tuxcall", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	185: SyscallMeta{SyscallName: "security", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	186: SyscallMeta{SyscallName: "gettid", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	187: SyscallMeta{SyscallName: "readahead", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "size_t"},
	}},
	188: SyscallMeta{SyscallName: "setxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	189: SyscallMeta{SyscallName: "lsetxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	190: SyscallMeta{SyscallName: "fsetxattr", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	191: SyscallMeta{SyscallName: "getxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	192: SyscallMeta{SyscallName: "lgetxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	193: SyscallMeta{SyscallName: "fgetxattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
	}},
	194: SyscallMeta{SyscallName: "listxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	195: SyscallMeta{SyscallName: "llistxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	196: SyscallMeta{SyscallName: "flistxattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	197: SyscallMeta{SyscallName: "removexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	198: SyscallMeta{SyscallName: "lremovexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
	}},
	199: SyscallMeta{SyscallName: "fremovexattr", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	200: SyscallMeta{SyscallName: "tkill", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	201: SyscallMeta{SyscallName: "time", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "old_time_t __user *"},
	}},
	202: SyscallMeta{SyscallName: "futex", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "u32 __user *"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "u32 __user *"},
		{KernelType: "unsigned int"},
	}},
	203: SyscallMeta{SyscallName: "sched_setaffinity", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long __user *"},
	}},
	204: SyscallMeta{SyscallName: "sched_getaffinity", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned long __user *"},
	}},
	205: SyscallMeta{SyscallName: "set_thread_area", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct user_desc __user *"},
	}},
	206: SyscallMeta{SyscallName: "io_setup", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned"},
		{KernelType: "aio_context_t __user *"},
	}},
	207: SyscallMeta{SyscallName: "io_destroy", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
	}},
	208: SyscallMeta{SyscallName: "io_getevents", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "struct io_event __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	209: SyscallMeta{SyscallName: "io_submit", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "int"},
		{KernelType: "uptr_t __user *"},
	}},
	210: SyscallMeta{SyscallName: "io_cancel", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "struct iocb __user *"},
		{KernelType: "struct io_event __user *"},
	}},
	211: SyscallMeta{SyscallName: "get_thread_area", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct user_desc __user *"},
	}},
	212: SyscallMeta{SyscallName: "lookup_dcookie", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "u64"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
	}},
	213: SyscallMeta{SyscallName: "epoll_create", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	214: SyscallMeta{SyscallName: "epoll_ctl_old", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	215: SyscallMeta{SyscallName: "epoll_wait_old", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	216: SyscallMeta{SyscallName: "remap_file_pages", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	217: SyscallMeta{SyscallName: "getdents64", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "struct linux_dirent64 __user *"},
		{KernelType: "unsigned int"},
	}},
	218: SyscallMeta{SyscallName: "set_tid_address", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
	}},
	219: SyscallMeta{SyscallName: "restart_syscall", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	220: SyscallMeta{SyscallName: "semtimedop", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sembuf __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
	}},
	221: SyscallMeta{SyscallName: "fadvise64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	222: SyscallMeta{SyscallName: "timer_create", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct sigevent __user *"},
		{KernelType: "timer_t __user *"},
	}},
	223: SyscallMeta{SyscallName: "timer_settime", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
		{KernelType: "struct itimerspec __user *"},
	}},
	224: SyscallMeta{SyscallName: "timer_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
		{KernelType: "struct itimerspec __user *"},
	}},
	225: SyscallMeta{SyscallName: "timer_getoverrun", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
	}},
	226: SyscallMeta{SyscallName: "timer_delete", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "timer_t"},
	}},
	227: SyscallMeta{SyscallName: "clock_settime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	228: SyscallMeta{SyscallName: "clock_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	229: SyscallMeta{SyscallName: "clock_getres", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timespec __user *"},
	}},
	230: SyscallMeta{SyscallName: "clock_nanosleep", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	231: SyscallMeta{SyscallName: "exit_group", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	232: SyscallMeta{SyscallName: "epoll_wait", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	233: SyscallMeta{SyscallName: "epoll_ctl", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
	}},
	234: SyscallMeta{SyscallName: "tgkill", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
	}},
	235: SyscallMeta{SyscallName: "utimes", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "struct old_timeval __user *"},
	}},
	236: SyscallMeta{SyscallName: "vserver", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
		{KernelType: ""},
	}},
	237: SyscallMeta{SyscallName: "mbind", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	238: SyscallMeta{SyscallName: "set_mempolicy", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
	}},
	239: SyscallMeta{SyscallName: "get_mempolicy", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	240: SyscallMeta{SyscallName: "mq_open", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "mode_t"},
		{KernelType: "struct mq_attr __user *"},
	}},
	241: SyscallMeta{SyscallName: "mq_unlink", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
	}},
	242: SyscallMeta{SyscallName: "mq_timedsend", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
	}},
	243: SyscallMeta{SyscallName: "mq_timedreceive", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int __user *"},
		{KernelType: "struct timespec __user *"},
	}},
	244: SyscallMeta{SyscallName: "mq_notify", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "struct sigevent __user *"},
	}},
	245: SyscallMeta{SyscallName: "mq_getsetattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "mqd_t"},
		{KernelType: "struct mq_attr __user *"},
		{KernelType: "struct mq_attr __user *"},
	}},
	246: SyscallMeta{SyscallName: "kexec_load", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "struct kexec_segment __user *"},
		{KernelType: "unsigned long"},
	}},
	247: SyscallMeta{SyscallName: "waitid", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "pid_t"},
		{KernelType: "struct siginfo __user *"},
		{KernelType: "int"},
		{KernelType: "struct rusage __user *"},
	}},
	248: SyscallMeta{SyscallName: "add_key", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "void __user *"},
		{KernelType: "size_t"},
		{KernelType: "key_serial_t"},
	}},
	249: SyscallMeta{SyscallName: "request_key", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "key_serial_t"},
	}},
	250: SyscallMeta{SyscallName: "keyctl", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	251: SyscallMeta{SyscallName: "ioprio_set", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	252: SyscallMeta{SyscallName: "ioprio_get", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	253: SyscallMeta{SyscallName: "inotify_init", NumArgs: 0, ArgInfo: []SyscallArgInfo{}},
	254: SyscallMeta{SyscallName: "inotify_add_watch", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	255: SyscallMeta{SyscallName: "inotify_rm_watch", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "__s32"},
	}},
	256: SyscallMeta{SyscallName: "migrate_pages", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long __user *"},
		{KernelType: "unsigned long __user *"},
	}},
	257: SyscallMeta{SyscallName: "openat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "umode_t"},
	}},
	258: SyscallMeta{SyscallName: "mkdirat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	259: SyscallMeta{SyscallName: "mknodat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
		{KernelType: "unsigned int"},
	}},
	260: SyscallMeta{SyscallName: "fchownat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "uid_t"},
		{KernelType: "gid_t"},
		{KernelType: "int"},
	}},
	261: SyscallMeta{SyscallName: "futimesat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct old_timeval __user *"},
	}},
	262: SyscallMeta{SyscallName: "newfstatat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct stat __user *"},
		{KernelType: "int"},
	}},
	263: SyscallMeta{SyscallName: "unlinkat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	264: SyscallMeta{SyscallName: "renameat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	265: SyscallMeta{SyscallName: "linkat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	266: SyscallMeta{SyscallName: "symlinkat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	267: SyscallMeta{SyscallName: "readlinkat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	268: SyscallMeta{SyscallName: "fchmodat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "umode_t"},
	}},
	269: SyscallMeta{SyscallName: "faccessat", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	270: SyscallMeta{SyscallName: "pselect6", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "fd_set __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "void __user *"},
	}},
	271: SyscallMeta{SyscallName: "ppoll", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct pollfd __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	272: SyscallMeta{SyscallName: "unshare", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
	}},
	273: SyscallMeta{SyscallName: "set_robust_list", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct robust_list_head __user *"},
		{KernelType: "size_t"},
	}},
	274: SyscallMeta{SyscallName: "get_robust_list", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct robust_list_head __user * __user *"},
		{KernelType: "size_t __user *"},
	}},
	275: SyscallMeta{SyscallName: "splice", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	276: SyscallMeta{SyscallName: "tee", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	277: SyscallMeta{SyscallName: "sync_file_range", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "loff_t"},
		{KernelType: "unsigned int"},
	}},
	278: SyscallMeta{SyscallName: "vmsplice", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	279: SyscallMeta{SyscallName: "move_pages", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned long"},
		{KernelType: "uptr_t __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	280: SyscallMeta{SyscallName: "utimensat", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "int"},
	}},
	281: SyscallMeta{SyscallName: "epoll_pwait", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct epoll_event __user *"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	282: SyscallMeta{SyscallName: "signalfd", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
	}},
	283: SyscallMeta{SyscallName: "timerfd_create", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	284: SyscallMeta{SyscallName: "eventfd", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
	}},
	285: SyscallMeta{SyscallName: "fallocate", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "loff_t"},
		{KernelType: "loff_t"},
	}},
	286: SyscallMeta{SyscallName: "timerfd_settime", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
		{KernelType: "struct itimerspec __user *"},
	}},
	287: SyscallMeta{SyscallName: "timerfd_gettime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct itimerspec __user *"},
	}},
	288: SyscallMeta{SyscallName: "accept4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct sockaddr __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	289: SyscallMeta{SyscallName: "signalfd4", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "sigset_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	290: SyscallMeta{SyscallName: "eventfd2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	291: SyscallMeta{SyscallName: "epoll_create1", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	292: SyscallMeta{SyscallName: "dup3", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	293: SyscallMeta{SyscallName: "pipe2", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	294: SyscallMeta{SyscallName: "inotify_init1", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	295: SyscallMeta{SyscallName: "preadv", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	296: SyscallMeta{SyscallName: "pwritev", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
	}},
	297: SyscallMeta{SyscallName: "rt_tgsigqueueinfo", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "siginfo_t __user *"},
	}},
	298: SyscallMeta{SyscallName: "perf_event_open", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct perf_event_attr __user *"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned long"},
	}},
	299: SyscallMeta{SyscallName: "recvmmsg", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct mmsghdr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "struct timespec __user *"},
	}},
	300: SyscallMeta{SyscallName: "fanotify_init", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	301: SyscallMeta{SyscallName: "fanotify_mark", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "__u64"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
	}},
	302: SyscallMeta{SyscallName: "prlimit64", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "unsigned int"},
		{KernelType: "struct rlimit64 __user *"},
		{KernelType: "struct rlimit64 __user *"},
	}},
	303: SyscallMeta{SyscallName: "name_to_handle_at", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "struct file_handle __user *"},
		{KernelType: "int __user *"},
		{KernelType: "int"},
	}},
	304: SyscallMeta{SyscallName: "open_by_handle_at", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct file_handle __user *"},
		{KernelType: "int"},
	}},
	305: SyscallMeta{SyscallName: "clock_adjtime", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "clockid_t"},
		{KernelType: "struct timex __user *"},
	}},
	306: SyscallMeta{SyscallName: "syncfs", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	307: SyscallMeta{SyscallName: "sendmmsg", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "struct mmsghdr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	308: SyscallMeta{SyscallName: "setns", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
	}},
	309: SyscallMeta{SyscallName: "getcpu", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned __user *"},
		{KernelType: "unsigned __user *"},
		{KernelType: "struct getcpu_cache __user *"},
	}},
	310: SyscallMeta{SyscallName: "process_vm_readv", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	311: SyscallMeta{SyscallName: "process_vm_writev", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	312: SyscallMeta{SyscallName: "kcmp", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "pid_t"},
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	313: SyscallMeta{SyscallName: "finit_module", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
	}},
	314: SyscallMeta{SyscallName: "sched_setattr", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_attr __user *"},
		{KernelType: "unsigned int"},
	}},
	315: SyscallMeta{SyscallName: "sched_getattr", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "pid_t"},
		{KernelType: "struct sched_attr __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
	}},
	316: SyscallMeta{SyscallName: "renameat2", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	317: SyscallMeta{SyscallName: "seccomp", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "void __user *"},
	}},
	318: SyscallMeta{SyscallName: "getrandom", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	319: SyscallMeta{SyscallName: "memfd_create", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "char __user *"},
		{KernelType: "unsigned int"},
	}},
	320: SyscallMeta{SyscallName: "kexec_file_load", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "int"},
		{KernelType: "unsigned long"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned long"},
	}},
	321: SyscallMeta{SyscallName: "bpf", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "union bpf_attr __user *"},
		{KernelType: "unsigned int"},
	}},
	322: SyscallMeta{SyscallName: "execveat", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "char __user * __user *"},
		{KernelType: "int"},
	}},
	323: SyscallMeta{SyscallName: "userfaultfd", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	324: SyscallMeta{SyscallName: "membarrier", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
	}},
	325: SyscallMeta{SyscallName: "mlock2", NumArgs: 3, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "int"},
	}},
	326: SyscallMeta{SyscallName: "copy_file_range", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "int"},
		{KernelType: "loff_t __user *"},
		{KernelType: "size_t"},
		{KernelType: "unsigned int"},
	}},
	327: SyscallMeta{SyscallName: "preadv2", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "rwf_t"},
	}},
	328: SyscallMeta{SyscallName: "pwritev2", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "struct iovec __user *"},
		{KernelType: "unsigned long"},
		{KernelType: "unsigned int"},
		{KernelType: "unsigned int"},
		{KernelType: "rwf_t"},
	}},
	329: SyscallMeta{SyscallName: "pkey_mprotect", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "size_t"},
		{KernelType: "unsigned long"},
		{KernelType: "int"},
	}},
	330: SyscallMeta{SyscallName: "pkey_alloc", NumArgs: 2, ArgInfo: []SyscallArgInfo{
		{KernelType: "unsigned long"},
		{KernelType: "unsigned long"},
	}},
	331: SyscallMeta{SyscallName: "pkey_free", NumArgs: 1, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
	}},
	332: SyscallMeta{SyscallName: "statx", NumArgs: 5, ArgInfo: []SyscallArgInfo{
		{KernelType: "int"},
		{KernelType: "char __user *"},
		{KernelType: "unsigned"},
		{KernelType: "unsigned int"},
		{KernelType: "struct statx __user *"},
	}},
	333: SyscallMeta{SyscallName: "io_pgetevents", NumArgs: 6, ArgInfo: []SyscallArgInfo{
		{KernelType: "aio_context_t"},
		{KernelType: "long"},
		{KernelType: "long"},
		{KernelType: "struct io_event __user *"},
		{KernelType: "struct timespec __user *"},
		{KernelType: "struct __aio_sigset __user *"},
	}},
	334: SyscallMeta{SyscallName: "rseq", NumArgs: 4, ArgInfo: []SyscallArgInfo{
		{KernelType: "struct rseq __user *"},
		{KernelType: "unsigned int"},
		{KernelType: "int"},
		{KernelType: "unsigned int"},
	}},
}
