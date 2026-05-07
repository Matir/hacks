package repl

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/Matir/hacks/go/asmsh/internal/arch"
	"github.com/Matir/hacks/go/asmsh/internal/engine"
	"github.com/Matir/hacks/go/asmsh/internal/formatter"
	"github.com/Matir/hacks/go/asmsh/internal/session"
	"github.com/peterh/liner"
)

type REPL struct {
	Session *session.Session
	Engine  *engine.Engine
	Liner   *liner.State
}

func NewREPL(s *session.Session) *REPL {
	l := liner.NewLiner()
	l.SetCtrlCAborts(true)
	return &REPL{
		Session: s,
		Liner:   l,
	}
}

func (r *REPL) Run() error {
	defer r.Liner.Close()

	for {
		prompt := fmt.Sprintf("asmsh (%s:%s)> ", r.Session.Arch, r.Session.Mode)
		line, err := r.Liner.Prompt(prompt)
		if err != nil {
			if err == io.EOF {
				fmt.Println("\nGoodbye!")
				return nil
			}
			if err == liner.ErrPromptAborted {
				fmt.Println("Aborted")
				continue
			}
			return err
		}

		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		r.Liner.AppendHistory(line)

		if strings.HasPrefix(line, ".") {
			if err := r.handleMetaCommand(line); err != nil {
				fmt.Printf("Error: %v\n", err)
			}
			continue
		}

		if err := r.handleInput(line); err != nil {
			fmt.Printf("Error: %v\n", err)
		}
	}
}

func (r *REPL) handleMetaCommand(line string) error {
	parts := strings.Fields(line)
	cmd := parts[0]
	args := parts[1:]

	switch cmd {
	case ".arch":
		if len(args) < 1 {
			return fmt.Errorf("usage: .arch <architecture>")
		}
		info, ok := arch.GetArch(args[0])
		if !ok {
			return fmt.Errorf("unsupported architecture: %s", args[0])
		}
		newEng, err := engine.NewEngine(info.Name)
		if err != nil {
			return err
		}
		r.Engine = newEng
		return r.Session.SetArch(info.Name)
	case ".mode":
		if len(args) < 1 {
			return fmt.Errorf("usage: .mode <assemble|disassemble>")
		}
		mode := session.Mode(args[0])
		if mode != session.ModeAssemble && mode != session.ModeDisassemble {
			return fmt.Errorf("invalid mode: %s", args[0])
		}
		r.Session.SetMode(mode)
	case ".offset":
		if len(args) < 1 {
			return fmt.Errorf("usage: .offset <address>")
		}
		addr, err := strconv.ParseUint(strings.TrimPrefix(args[0], "0x"), 16, 64)
		if err != nil {
			// Try decimal if hex fails
			addr, err = strconv.ParseUint(args[0], 10, 64)
			if err != nil {
				return fmt.Errorf("invalid address: %s", args[0])
			}
		}
		r.Session.SetOffset(addr)
	case ".output":
		if len(args) < 1 {
			return fmt.Errorf("usage: .output <pretty|c|python>")
		}
		r.Session.Output = args[0]
	case ".symbols":
		for name, addr := range r.Session.Symbols {
			fmt.Printf("%s: 0x%x\n", name, addr)
		}
	case ".clear":
		r.Session.Clear()
		fmt.Println("Session cleared.")
	case ".exit", ".quit":
		fmt.Println("Goodbye!")
		os.Exit(0)
	default:
		return fmt.Errorf("unknown meta-command: %s", cmd)
	}
	return nil
}

func (r *REPL) handleInput(line string) error {
	line = StripComments(line)
	if line == "" {
		return nil
	}

	if r.Session.Mode == session.ModeAssemble {
		bytes, err := r.Engine.Assembler.Assemble(line, r.Session.Offset, r.Session.Symbols)
		if err != nil {
			return err
		}
		fmt.Println(formatter.Format(r.Session.Output, r.Session.Offset, bytes, line))
		r.Session.Offset += uint64(len(bytes))
	} else {
		data, err := ParseHex(line)
		if err != nil {
			return err
		}

		asm, err := r.Engine.Disassembler.Disassemble(data, r.Session.Offset)
		if err != nil {
			return err
		}
		fmt.Println(formatter.Format(r.Session.Output, r.Session.Offset, data, asm))
		r.Session.Offset += uint64(len(data))
	}
	return nil
}
