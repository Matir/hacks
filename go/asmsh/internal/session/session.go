package session

type Mode string

const (
	ModeAssemble    Mode = "assemble"
	ModeDisassemble Mode = "disassemble"
)

type Session struct {
	Arch    string
	Mode    Mode
	Offset  uint64
	Symbols map[string]uint64
	Output  string // Current output format
}

func NewSession() *Session {
	return &Session{
		Arch:    "x86_64", // Default
		Mode:    ModeAssemble,
		Offset:  0,
		Symbols: make(map[string]uint64),
		Output:  "pretty",
	}
}

func (s *Session) Clear() {
	s.Offset = 0
	s.Symbols = make(map[string]uint64)
}

func (s *Session) SetArch(arch string) error {
	// TODO: Validate arch
	s.Arch = arch
	return nil
}

func (s *Session) SetMode(mode Mode) {
	s.Mode = mode
}

func (s *Session) SetOffset(offset uint64) {
	s.Offset = offset
}

func (s *Session) AddSymbol(name string, addr uint64) {
	s.Symbols[name] = addr
}

func (s *Session) GetSymbol(name string) (uint64, bool) {
	addr, ok := s.Symbols[name]
	return addr, ok
}
