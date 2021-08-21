package main

import (
	"fmt"
	"os"

	"github.com/Matir/hacks/go/tracer/ptrace"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <program> [args]\n", os.Args[0])
		os.Exit(1)
	}
	traceEvts, err := ptrace.TraceProcess(os.Args[1:])
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error starting trace: %s\n", err)
		os.Exit(1)
	}
	for e := range traceEvts {
		fmt.Printf("%s\n", e.String())
	}
}
