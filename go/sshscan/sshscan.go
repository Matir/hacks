package main

import (
	"crypto/dsa"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/rsa"
	"errors"
	"fmt"
	"net"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
)

var ScanAlgos = []string{
	ssh.KeyAlgoRSA,
	ssh.KeyAlgoDSA,
	ssh.KeyAlgoECDSA256,
	ssh.KeyAlgoECDSA384,
	ssh.KeyAlgoECDSA521,
	ssh.KeyAlgoED25519,
}

var (
	ErrNextAlgo = errors.New("Next algorithm please!")
)

func main() {
	for _, a := range ScanAlgos {
		cfg := ssh.ClientConfig{
			HostKeyAlgorithms: []string{a},
			Timeout:           30 * time.Second,
			HostKeyCallback: func(hostname string, remote net.Addr, key ssh.PublicKey) error {
				fmt.Println(key.Type() + ": " + ssh.FingerprintSHA256(key))
				return ErrNextAlgo
			},
		}
		client, err := ssh.Dial("tcp", "192.168.50.6:22", &cfg)
		if err != nil {
			if !strings.HasSuffix(err.Error(), ErrNextAlgo.Error()) {
				fmt.Println(err)
			}
		} else {
			defer client.Close()
		}
	}
}

type HostScanner struct {
	host           string
	port           uint16
	remainingAlgos []string
}

func NewHostScanner(host string) *HostScanner {
	return &HostScanner{
		remainingAlgos: ScanAlgos[:],
		port:           22,
		host:           host,
	}
}

func (hs *HostScanner) removeAlgo(algo string) {
	l := len(hs.remainingAlgos)
	for i, v := range hs.remainingAlgos {
		if v == algo {
			hs.remainingAlgos[i] = hs.remainingAlgos[l-1]
			hs.remainingAlgos = hs.remainingAlgos[:l-1]
			return
		}
	}
}

func (hs *HostScanner) hostKeyCallback(hostname string, remote net.Addr, key ssh.PublicKey) error {
	algo := key.Type()
	hs.removeAlgo(algo)
	// Extract key-specific data
	if cpki, ok := key.(ssh.CryptoPublicKey); ok {
		switch cpk := cpki.CryptoPublicKey().(type) {
		case *rsa.PublicKey:
		case *dsa.PublicKey:
		case *ecdsa.PublicKey:
		case ed25519.PublicKey:
		default:
			fmt.Printf("Couldn't find underlying type for %s\n", algo)
		}
	} else {
		fmt.Printf("Can't get crypto.PublicKey for %s\n", algo)
	}
	return ErrNextAlgo
}
