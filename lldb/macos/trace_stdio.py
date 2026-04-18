import lldb

def __lldb_init_module(debugger, internal_dict):
    # Break on the system 'write' call
    # File descriptor 1 is stdout, 2 is stderr
    target = debugger.GetSelectedTarget()
    # We use __write because write is a syscall wrapper in libsystem_kernel.dylib
    bp = target.BreakpointCreateByName("__write")
    bp.SetAutoContinue(True)
    bp.SetScriptCallbackFunction("trace_write.log_write")

def log_write(frame, bp_loc, dict):
    # x0: file descriptor, x1: buffer pointer, x2: count (ARM64)
    fd = frame.FindRegister("x0").GetValueAsUnsigned()
    if fd == 1 or fd == 2:
        label = "STDOUT" if fd == 1 else "STDERR"
        buf_addr = frame.FindRegister("x1").GetValueAsUnsigned()
        count = frame.FindRegister("x2").GetValueAsUnsigned()

        error = lldb.SBError()
        content = frame.GetThread().GetProcess().ReadCStringFromMemory(buf_addr, count + 1, error)
        if content:
            print(f"[{label}]: {content.strip()}")
