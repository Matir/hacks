package session

import (
	"testing"
)

func TestSession(t *testing.T) {
	s := NewSession()
	if s.Arch != "x86_64" {
		t.Errorf("NewSession default arch = %v, want x86_64", s.Arch)
	}

	s.AddSymbol("test", 0x1234)
	if addr, ok := s.GetSymbol("test"); !ok || addr != 0x1234 {
		t.Errorf("GetSymbol('test') = 0x%x, %v; want 0x1234, true", addr, ok)
	}

	s.Clear()
	if len(s.Symbols) != 0 {
		t.Errorf("Clear() failed to clear symbols")
	}
	if s.Offset != 0 {
		t.Errorf("Clear() failed to reset offset")
	}
}
