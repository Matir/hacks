import lldb

def __lldb_init_module(debugger, internal_dict):
    # set a breakpoint on the function that starts new processes
    debugger.HandleCommand('breakpoint set -n posix_spawn -G1 -C "script trace_exec.log_spawn()"')

def log_spawn():
    # Get the first argument (path to the executable)
    # On macOS x86_64/arm64, this is usually in the first register (rdi or x0)
    frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()

    # This reaches into the CPU registers to grab the path of the child process
    # x0 is the standard register for the first argument on Apple Silicon
    path_addr = frame.FindRegister("x0").GetValueAsUnsigned()
    error = lldb.SBError()
    path = lldb.debugger.GetSelectedTarget().GetProcess().ReadCStringFromMemory(path_addr, 512, error)

    print(f"[LLVM-Child-Spawn] Executing: {path}")
