package main

import (
	"fmt"
	"os"

	"github.com/Matir/hacks/go/asmsh/internal/arch"
	"github.com/Matir/hacks/go/asmsh/internal/engine"
	"github.com/Matir/hacks/go/asmsh/internal/repl"
	"github.com/Matir/hacks/go/asmsh/internal/session"
	"github.com/spf13/cobra"
)

var (
	defaultArch string
	offset      string
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "asmsh",
		Short: "ASM Shell is an interactive assembler and disassembler",
		Run: func(cmd *cobra.Command, args []string) {
			runREPL(session.ModeAssemble)
		},
	}

	rootCmd.PersistentFlags().StringVarP(&defaultArch, "arch", "a", "x86_64", "Architecture to use")
	rootCmd.PersistentFlags().StringVarP(&offset, "offset", "o", "0", "Starting offset")

	asmCmd := &cobra.Command{
		Use:   "assemble",
		Short: "Start in assembly mode",
		Run: func(cmd *cobra.Command, args []string) {
			runREPL(session.ModeAssemble)
		},
	}

	disasmCmd := &cobra.Command{
		Use:   "disassemble",
		Short: "Start in disassembly mode",
		Run: func(cmd *cobra.Command, args []string) {
			runREPL(session.ModeDisassemble)
		},
	}

	rootCmd.AddCommand(asmCmd, disasmCmd)

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func runREPL(mode session.Mode) {
	s := session.NewSession()
	s.SetMode(mode)

	info, ok := arch.GetArch(defaultArch)
	if !ok {
		fmt.Printf("Error: unsupported architecture: %s\n", defaultArch)
		os.Exit(1)
	}

	if err := s.SetArch(info.Name); err != nil {
		fmt.Printf("Error setting architecture: %v\n", err)
		os.Exit(1)
	}

	r := repl.NewREPL(s)
	eng, err := engine.NewEngine(info.Name)
	if err != nil {
		fmt.Printf("Error creating engine: %v\n", err)
		os.Exit(1)
	}
	r.Engine = eng

	if err := r.Run(); err != nil {
		fmt.Printf("REPL Error: %v\n", err)
		os.Exit(1)
	}
}
