package repl

import (
	"bytes"
	"testing"
)

func TestStripComments(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"nop // do nothing", "nop"},
		{"xor rax, rax # zero rax", "xor rax, rax"},
		{"inc rcx; increment", "inc rcx"},
		{"  nop  ", "nop"},
	}
	for _, tt := range tests {
		if got := StripComments(tt.input); got != tt.want {
			t.Errorf("StripComments(%q) = %q, want %q", tt.input, got, tt.want)
		}
	}
}

func TestParseHex(t *testing.T) {
	tests := []struct {
		input   string
		want    []byte
		wantErr bool
	}{
		{"904831c0", []byte{0x90, 0x48, 0x31, 0xc0}, false},
		{"90 48 31 c0", []byte{0x90, 0x48, 0x31, 0xc0}, false},
		{"0x90, 0x48", []byte{0x90, 0x48}, false},
		{"\\x90\\x48", []byte{0x90, 0x48}, false},
		{"904", nil, true}, // Odd length
		{"GG", nil, true},  // Invalid hex
	}
	for _, tt := range tests {
		got, err := ParseHex(tt.input)
		if (err != nil) != tt.wantErr {
			t.Errorf("ParseHex(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			continue
		}
		if err == nil && !bytes.Equal(got, tt.want) {
			t.Errorf("ParseHex(%q) = %v, want %v", tt.input, got, tt.want)
		}
	}
}
