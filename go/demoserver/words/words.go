package words

//go:generate bash ./words_to_vars.sh

import (
	"math/rand"
)

func makeRandomChooser(opts []string) func() string {
	return func() string {
		n := rand.Intn(len(opts))
		return opts[n]
	}
}

var (
	DirectoryRandomChooser = makeRandomChooser(directories)
	UsernameRandomChooser  = makeRandomChooser(usernames)
	PasswordRandomChooser  = makeRandomChooser(passwords)
)
