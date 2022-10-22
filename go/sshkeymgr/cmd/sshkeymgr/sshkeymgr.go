package main

import (
	"context"
	"flag"
	"os"

	"github.com/google/subcommands"
)

type updateFileCommand struct {
	removeUnmanaged bool
	onlyAdd         bool
}

func (*updateFileCommand) Name() string { return "update" }
func (*updateFileCommand) Synopsis() string {
	return "Update authorized_keys from a directory of keys."
}
func (*updateFileCommand) Usage() string {
	return `update:
	Update an SSH authorized_keys file.
	`
}
func (c *updateFileCommand) SetFlags(f *flag.FlagSet) {
	f.BoolVar(&c.removeUnmanaged, "remove-unmanaged", false, "Remove all unmanaged keys.")
	f.BoolVar(&c.onlyAdd, "add-only", false, "Only add keys, do not remove.")
}
func (c *updateFileCommand) Execute(_ context.Context, f *flag.FlagSet, _ ...interface{}) subcommands.ExitStatus {
	return subcommands.ExitSuccess
}

func main() {
	subcommands.Register(&updateFileCommand{}, "")

	flag.Parse()
	ctx := context.Background()
	os.Exit(int(subcommands.Execute(ctx)))
}
