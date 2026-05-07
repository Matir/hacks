//go:build !mock

package engine

import (
	"fmt"

	"github.com/Matir/hacks/go/asmsh/internal/arch"
)

func NewEngine(archName string) (*Engine, error) {
	info, ok := arch.GetArch(archName)
	if !ok {
		return nil, fmt.Errorf("unsupported architecture: %s", archName)
	}

	ks, err := newKeystoneAssembler(info)
	if err != nil {
		return nil, err
	}

	cs, err := newCapstoneDisassembler(info)
	if err != nil {
		ks.Close()
		return nil, err
	}

	return &Engine{
		Assembler:    ks,
		Disassembler: cs,
	}, nil
}
