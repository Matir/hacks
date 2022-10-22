package sshkeymgr

import (
	"bufio"
	"fmt"
	"io"
	"strings"
	"time"

	"golang.org/x/crypto/ssh"
)

const (
	MANAGED_TAG = "sshkeymgr:"
)

type KeySet struct {
	Keys []*KeyData
}

func LoadKeySet(r io.Reader) (*KeySet, error) {
	ks := &KeySet{}
	scanner := bufio.NewScanner(r)
	for {
		if kd, err := ReadKeydataFromScanner(scanner); err != nil {
			return nil, err
		} else if kd == nil {
			// EOF, normal
			return ks, nil
		} else {
			ks.Keys = append(ks.Keys, kd)
		}
	}
}

func (ks *KeySet) WriteKeySet(w io.Writer) error {
	for _, k := range ks.Keys {
		if err := k.WriteKeydata(w); err != nil {
			return err
		}
	}
	return nil
}

type KeyData struct {
	comments   []string
	pubkeyline string
	pubkey     ssh.PublicKey
	managed    bool
	shortname  string
}

func ReadKeydataFromScanner(sc *bufio.Scanner) (*KeyData, error) {
	lines := make([]string, 0)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" && len(lines) == 0 {
			continue
		}
		lines = append(lines, line)
		if !strings.HasPrefix(line, "#") {
			// We've read	through a line with a key
			return LoadKeydata(lines)
		}
	}
	if err := sc.Err(); err != nil {
		return nil, fmt.Errorf("Error scanning data: %w", err)
	}
	if len(lines) == 0 {
		// No more keys
		return nil, nil
	}
	return nil, fmt.Errorf("No keydata found in file.")
}

func LoadKeydata(lines []string) (*KeyData, error) {
	kd := &KeyData{}
	for _, line := range lines {
		if strings.HasPrefix(line, "#") {
			if strings.Contains(line, MANAGED_TAG) {
				kd.managed = true
			}
			kd.comments = append(kd.comments, line)
			continue
		}
		if kd.pubkey != nil {
			return nil, fmt.Errorf("More than one public key in loading!")
		}
		pk, _, _, _, err := ssh.ParseAuthorizedKey([]byte(line))
		if err != nil {
			return nil, fmt.Errorf("Error parsing authorized key line: %w", err)
		}
		kd.pubkey = pk
		kd.pubkeyline = line
	}
	if kd.pubkey == nil {
		return nil, fmt.Errorf("No public key line in LoadKeydata")
	}
	return kd, nil
}

func (kd *KeyData) MatchesPubkey(pk string) bool {
	return ssh.FingerprintSHA256(kd.pubkey) == pk || ssh.FingerprintLegacyMD5(kd.pubkey) == pk
}

func (kd *KeyData) WriteKeydata(w io.Writer) error {
	_, err := fmt.Fprintf(w, "%s\n%s\n", strings.Join(kd.comments, "\n"), kd.pubkeyline)
	return err
}

func (kd *KeyData) AddManagedComment() {
	if kd.managed {
		return
	}
	date := time.Now().Format("2006-01-02")
	line := fmt.Sprintf("# %s (Added %s as %s) [%s]",
		MANAGED_TAG, date, kd.shortname, ssh.FingerprintSHA256(kd.pubkey))
	kd.comments = append(kd.comments, line)
	kd.managed = true
}
