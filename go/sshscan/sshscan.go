package main

import (
	"errors"
	"fmt"
	"log"
	"net"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
)

const (
	ConnectTimeout = 30 * time.Second
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
	hs := NewHostScanner("192.168.50.6")
	if err := hs.scan(); err != nil {
		log.Println(err)
	}
	fmt.Println(hs.VerboseString())
}

type HostScanner struct {
	host           string
	port           uint16
	remainingAlgos []string
	keyData        map[string]string
	keyFP          map[string]string
}

func NewHostScanner(host string) *HostScanner {
	return &HostScanner{
		remainingAlgos: ScanAlgos[:],
		port:           22,
		host:           host,
		keyFP:          make(map[string]string),
		keyData:        make(map[string]string),
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
	hs.keyFP[algo] = ssh.FingerprintSHA256(key)
	hs.keyData[algo] = string(ssh.MarshalAuthorizedKey(key))
	return ErrNextAlgo
}

func (hs *HostScanner) scanOne() error {
	cfg := ssh.ClientConfig{
		HostKeyAlgorithms: hs.remainingAlgos[:],
		Timeout:           ConnectTimeout,
		HostKeyCallback:   hs.hostKeyCallback,
	}
	endpoint := fmt.Sprintf("%s:%d", hs.host, hs.port)
	client, err := ssh.Dial("tcp", endpoint, &cfg)
	if err != nil {
		if !strings.HasSuffix(err.Error(), ErrNextAlgo.Error()) {
			return err
		}
	} else {
		defer client.Close()
	}
	return nil
}

func (hs *HostScanner) scan() error {
	for len(hs.remainingAlgos) > 0 {
		if err := hs.scanOne(); err != nil {
			if strings.Contains(err.Error(), "no common algorithm for host key") {
				// We just exhausted matching algos, no problem.
				return nil
			}
			return err
		}
	}
	// Got all the algos we support
	return nil
}

func (hs *HostScanner) VerboseString() string {
	meta := fmt.Sprintf("%s:%d\n", hs.host, hs.port)
	builder := new(strings.Builder)
	builder.WriteString(meta)
	maxLen := 0
	for _, t := range ScanAlgos {
		l := len(t)
		if l > maxLen {
			maxLen = l
		}
	}
	for t, fp := range hs.keyFP {
		builder.WriteString(fmt.Sprintf("    %*s %s\n", maxLen, t, fp))
	}
	return builder.String()
}
