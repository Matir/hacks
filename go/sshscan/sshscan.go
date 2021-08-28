package main

import (
	"errors"
	"fmt"
	"net"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
)

const (
	ConnectTimeout = 5 * time.Second
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
	// Not sure why this is not exported in the ssh package...
	SupportedCiphers = []string{
		"aes128-ctr", "aes192-ctr", "aes256-ctr",
		"aes128-gcm@openssh.com",
		"chacha20-poly1305@openssh.com",
		"arcfour256", "arcfour128", "arcfour",
		"aes128-cbc", "3des-cbc",
	}
	SupportedKexAlgos = []string{
		"curve25519-sha256@libssh.org",
		"ecdh-sha2-nistp256",
		"ecdh-sha2-nistp384",
		"ecdh-sha2-nistp521",
		"diffie-hellman-group14-sha1",
		"diffie-hellman-group1-sha1",
	}
)

type HostScanner struct {
	Host           string
	Port           uint16
	remainingAlgos []string
	KeyData        map[string]string
	KeyFP          map[string]string
	ServerVersion  string
	ScanStart      time.Time
}

func NewHostScanner(host string) *HostScanner {
	return &HostScanner{
		remainingAlgos: ScanAlgos[:],
		Port:           22,
		Host:           host,
		KeyFP:          make(map[string]string),
		KeyData:        make(map[string]string),
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
	hs.KeyFP[algo] = ssh.FingerprintSHA256(key)
	hs.KeyData[algo] = string(ssh.MarshalAuthorizedKey(key))
	return ErrNextAlgo
}

func (hs *HostScanner) scanOne() error {
	cfg := ssh.ClientConfig{
		Config: ssh.Config{
			Ciphers:      SupportedCiphers,
			KeyExchanges: SupportedKexAlgos,
		},
		HostKeyAlgorithms: hs.remainingAlgos[:],
		Timeout:           ConnectTimeout,
		HostKeyCallback:   hs.hostKeyCallback,
	}
	endpoint := fmt.Sprintf("%s:%d", hs.Host, hs.Port)
	conn, err := net.DialTimeout("tcp", endpoint, cfg.Timeout)
	if err != nil {
		return err
	}
	connLogger := &ConnLogger{Conn: conn}
	c, _, _, err := ssh.NewClientConn(connLogger, endpoint, &cfg)
	if c != nil {
		defer c.Close()
	}
	if hs.ServerVersion == "" {
		hs.ServerVersion = strings.TrimSpace(string(connLogger.GetFirstLine()))
	}
	if err != nil {
		if !strings.HasSuffix(err.Error(), ErrNextAlgo.Error()) {
			return err
		}
	}
	return nil
}

func (hs *HostScanner) Scan() error {
	hs.ScanStart = time.Now().UTC()
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
	meta := fmt.Sprintf("%s:%d\n", hs.Host, hs.Port)
	builder := new(strings.Builder)
	builder.WriteString(meta)
	if hs.ServerVersion != "" {
		builder.WriteString(hs.ServerVersion)
		builder.WriteString("\n")
	}
	maxLen := 0
	for _, t := range ScanAlgos {
		l := len(t)
		if l > maxLen {
			maxLen = l
		}
	}
	for t, fp := range hs.KeyFP {
		builder.WriteString(fmt.Sprintf("    %*s %s\n", maxLen, t, fp))
	}
	return builder.String()
}
