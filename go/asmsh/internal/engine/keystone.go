//go:build !mock

package engine

import (
	"fmt"

	"github.com/Matir/hacks/go/asmsh/internal/arch"
	"github.com/keystone-engine/keystone/bindings/go/keystone"
)

type keystoneAssembler struct {
	arch arch.ArchInfo
	ks   *keystone.Keystone
}

func newKeystoneAssembler(info arch.ArchInfo) (*keystoneAssembler, error) {
	ks, err := keystone.New(keystone.Architecture(info.KSArch), keystone.Mode(info.KSMode))
	if err != nil {
		return nil, fmt.Errorf("failed to initialize keystone: %v", err)
	}
	return &keystoneAssembler{
		arch: info,
		ks:   ks,
	}, nil
}

func (a *keystoneAssembler) Assemble(mnemonic string, offset uint64, symbols map[string]uint64) ([]byte, error) {
	// TODO: Handle symbol resolution. Keystone's Go bindings don't expose 
	// a symbol resolver callback easily, so we might need to pre-process the string.
	insns, _, ok := a.ks.Assemble(mnemonic, offset)
	if !ok {
		return nil, fmt.Errorf("assembly failed: %v", a.ks.LastError())
	}
	return insns, nil
}

func (a *keystoneAssembler) Close() {
	if a.ks != nil {
		a.ks.Close()
	}
}
