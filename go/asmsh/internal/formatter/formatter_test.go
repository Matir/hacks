package formatter

import (
	"testing"
)

func TestFormatPretty(t *testing.T) {
	offset := uint64(0x1000)
	bytes := []byte{0x90, 0x48, 0x31, 0xc0}
	asm := "nop; xor rax, rax"
	got := FormatPretty(offset, bytes, asm)
	// 90 48 31 c0 (11 chars) + 1 space from loop = 12 chars.
	// %-20s adds 8 padding spaces. Total 20 chars in the bytes field.
	// 12 (bytes+loop space) + 8 (padding) = 20.
	// So 1 (loop space) + 8 (padding) = 9 spaces after 'c0'.
	want := "0x00001000 | 90 48 31 c0          | nop; xor rax, rax"
	if got != want {
		t.Errorf("FormatPretty() = %q, want %q", got, want)
	}
}

func TestFormatCArray(t *testing.T) {
	bytes := []byte{0x90, 0x48}
	got := FormatCArray(bytes)
	want := "{ 0x90, 0x48 }"
	if got != want {
		t.Errorf("FormatCArray() = %q, want %q", got, want)
	}
}

func TestFormatPythonArray(t *testing.T) {
	bytes := []byte{0x90, 0x48}
	got := FormatPythonArray(bytes)
	want := "b\"\\x90\\x48\""
	if got != want {
		t.Errorf("FormatPythonArray() = %q, want %q", got, want)
	}
}

func TestFormat(t *testing.T) {
	bytes := []byte{0x90}
	asm := "nop"
	offset := uint64(0)

	tests := []struct {
		format string
		want   string
	}{
		{"c", "{ 0x90 }"},
		{"python", "b\"\\x90\""},
		{"pretty", "0x00000000 | 90                   | nop"},
	}

	for _, tt := range tests {
		t.Run(tt.format, func(t *testing.T) {
			if got := Format(tt.format, offset, bytes, asm); got != tt.want {
				t.Errorf("Format(%s) = %q, want %q", tt.format, got, tt.want)
			}
		})
	}
}
