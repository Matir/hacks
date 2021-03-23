package ptrace

import (
	"os/exec"
	"runtime"
	"syscall"
)

type TraceEvent struct {
}

func TraceProcess(args []string) (<-chan *TraceEvent, error) {
	errChan := make(chan error)
	resChan := make(chan *TraceEvent, 10) //Arbitrary capacity

	go traceProcessInternal(args, resChan, errChan)

	return resChan, <-errChan
}

func traceProcessInternal(args []string, evts chan<- *TraceEvent, errs chan<- error) {
	defer close(errs)
	defer close(evts)
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	// Ok, start the real work here
	cmd := exec.Command(args[0], args[1:]...)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Ptrace: true,
	}
	if err := cmd.Start(); err != nil {
		errs <- err
		return
	}

	opts := syscall.PTRACE_O_EXITKILL
	opts |= syscall.PTRACE_O_TRACECLONE
	opts |= syscall.PTRACE_O_TRACEFORK
	opts |= syscall.PTRACE_O_TRACEVFORK
	if err := syscall.PtraceSetOptions(cmd.Process.Pid, opts); err != nil {
		cmd.Process.Kill()
		errs <- err
		return
	}

	errs <- nil

	// Now actually trace stuff
	for {
	}
}
