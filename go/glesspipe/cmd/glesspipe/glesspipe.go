package main

import (
	"fmt"
	"io"
	"os"

	"github.com/Matir/hacks/go/glesspipe"
)

func main() {
	var fp io.ReadCloser
	var fname string
	if len(os.Args) == 1 || os.Args[1] == "-" {
		fp = os.Stdin
		fname = "-"
	} else {
		fname = os.Args[1]
		lfp, err := os.Open(os.Args[1])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Failed opening file %s: %v\n", os.Args[1], err)
			os.Exit(1)
		}
		fp = lfp
	}
	defer fp.Close()
	piper := glesspipe.NewGlessPipe()
	if err := piper.Run(fname, fp, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "Failed processing: %v\n", err)
		os.Exit(1)
	}
}
