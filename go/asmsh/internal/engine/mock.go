//go:build mock

package engine

type MockEngine struct{}

func (m *MockEngine) Assemble(mnemonic string, offset uint64, symbols map[string]uint64) ([]byte, error) {
	return []byte{0x90}, nil // Always NOP
}

func (m *MockEngine) Disassemble(data []byte, offset uint64) (string, error) {
	return "nop", nil
}

func NewEngine(arch string) (*Engine, error) {
	return &Engine{
		Assembler:    &MockEngine{},
		Disassembler: &MockEngine{},
	}, nil
}
