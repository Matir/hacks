package acmedns

import (
	"fmt"
)

// This is a stub DNS Provider for testing
type StubDNSProvider struct {
	data map[string]string
}

var stubProvider = StubDNSProvider{
	data: make(map[string]string),
}

func NewStubDNSProvider() *StubDNSProvider {
	return &StubDNSProvider{
		data: make(map[string]string),
	}
}

func (s *StubDNSProvider) GetTXT(name string) (string, error) {
	if v, ok := s.data[name]; ok {
		return v, nil
	}
	return "", fmt.Errorf("No entry for %v", name)
}

func (s *StubDNSProvider) SetTXT(name, value string) (string, error) {
	s.data[name] = value
	return value, nil
}

func (s *StubDNSProvider) DeleteTXT(name string) error {
	delete(s.data, name)
	return nil
}
