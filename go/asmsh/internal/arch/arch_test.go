package arch

import (
	"testing"
)

func TestGetArch(t *testing.T) {
	tests := []struct {
		name     string
		wantName string
		wantOk   bool
	}{
		{"x86_64", "x86_64", true},
		{"X86_64", "x86_64", true},
		{"arm64", "arm64", true},
		{"ARM64", "arm64", true},
		{"invalid", "", false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := GetArch(tt.name)
			if ok != tt.wantOk {
				t.Errorf("GetArch() ok = %v, want %v", ok, tt.wantOk)
				return
			}
			if ok && got.Name != tt.wantName {
				t.Errorf("GetArch() got.Name = %v, want %v", got.Name, tt.wantName)
			}
		})
	}
}
