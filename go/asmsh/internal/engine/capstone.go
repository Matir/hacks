//go:build !mock

package engine

import (
	"fmt"

	"github.com/Matir/hacks/go/asmsh/internal/arch"
	"github.com/knightsc/gapstone"
)

type capstoneDisassembler struct {
	arch arch.ArchInfo
	cs   gapstone.Engine
}

func newCapstoneDisassembler(info arch.ArchInfo) (*capstoneDisassembler, error) {
	cs, err := gapstone.New(info.CSArch, info.CSMode)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize capstone: %v", err)
	}
	return &capstoneDisassembler{
		arch: info,
		cs:   cs,
	}, nil
}

func (d *capstoneDisassembler) Disassemble(data []byte, offset uint64) (string, error) {
	insns, err := d.cs.Disasm(data, offset, 0)
	if err != nil {
		return "", fmt.Errorf("disassembly failed: %v", err)
	}
	if len(insns) == 0 {
		return "", fmt.Errorf("no instructions disassembled")
	}
	// For now, we return just the first instruction since the REPL 
	// currently processes one logical unit at a time.
	return fmt.Sprintf("%s %s", insns[0].Mnemonic, insns[0].OpStr), nil
}

func (d *capstoneDisassembler) Close() {
	d.cs.Close()
}
