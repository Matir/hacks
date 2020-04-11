package main

import (
	"bytes"
	"crypto/rsa"
	"fmt"
	"golang.org/x/crypto/openpgp"
	"io/ioutil"
	"os"
	"os/exec"
	"sync"
)

const (
	Workers       = 5
	KeysPerWorker = 10000
)

func main() {
	var wg sync.WaitGroup
	wg.Add(Workers)
	for i := 0; i < Workers; i++ {
		go func() {
			defer wg.Done()
			for j := 0; j < KeysPerWorker; j++ {
				if err := doOneKey(); err != nil {
					fmt.Printf("ugh, error working: %s\n", err)
					return
				}
			}
		}()
	}
	wg.Wait()
}

func doOneKey() error {
	dname, err := ioutil.TempDir("", "gpgcheck")
	if err != nil {
		fmt.Printf("Error creating tempdir: %s\n", err)
		return err
	}
	shouldRemove := false
	defer func() {
		if shouldRemove {
			if err := os.RemoveAll(dname); err != nil {
				fmt.Printf("Error removing directory: %s\n", err)
			}
		}
	}()
	shouldRemove, err = checkKey(dname)
	if err != nil {
		fmt.Printf("Error checking key: %s\n", err)
		return err
	}
	return nil
}

func checkKey(dirname string) (bool, error) {
	env := os.Environ()
	env = append(env, fmt.Sprintf("GNUPGHOME=%s", dirname))
	// Do the generation
	cmd := exec.Command("/usr/bin/gpg", "--batch", "--passphrase", "", "--quick-gen-key", "foobar", "rsa")
	cmd.Env = env
	cmd.Dir = dirname
	var buf bytes.Buffer
	cmd.Stderr = &buf
	if err := cmd.Run(); err != nil {
		fmt.Printf("Error running keygen: %s\n", err)
		fmt.Printf("%s\n", buf.String())
		return false, err
	}

	// Do the export
	cmd = exec.Command("/usr/bin/gpg", "--armor", "--export-secret-key")
	cmd.Env = env
	cmd.Dir = dirname
	keysrc, err := cmd.StdoutPipe()
	if err := cmd.Start(); err != nil {
		fmt.Printf("Error starting export: %s", err)
		return false, err
	}
	defer func() {
		cmd.Wait()
		cmd = exec.Command("/usr/bin/gpgconf", "--kill", "gpg-agent")
		cmd.Env = env
		cmd.Dir = dirname
		cmd.Run()
	}()

	// Process the key
	elist, err := openpgp.ReadArmoredKeyRing(keysrc)
	if err != nil {
		return false, err
	}
	for _, e := range elist {
		if e.PrivateKey != nil {
			continue
		}
		switch pk := e.PrivateKey.PrivateKey.(type) {
		case *rsa.PrivateKey:
			for _, prime := range pk.Primes {
				if !prime.ProbablyPrime(32) {
					// Oh shit!
					fmt.Printf("Invalid private key: %s", dirname)
					return false, nil
				}
			}
		default:
			fmt.Printf("Unknown private key type!")
		}
	}
	return true, nil
}
