package engine

type Assembler interface {
	Assemble(mnemonic string, offset uint64, symbols map[string]uint64) ([]byte, error)
}

type Disassembler interface {
	Disassemble(data []byte, offset uint64) (string, error)
}

type Engine struct {
	Assembler    Assembler
	Disassembler Disassembler
}
