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

// Removes any keys matching the keyspec.
// We expect either a public key or an MD5 or SHA256 based fingerprint.
// Returns true if found, false if not found
func (ks *KeySet) RemoveKeyBySpec(spec string) bool {
	// Try if this looks like a key
	if pk, _, _, _, err := ssh.ParseAuthorizedKey([]byte(spec)); err == nil {
		spec = ssh.FingerprintSHA256(pk)
	}
	left := ks.Keys[:0]
	found := false
	for _, k := range ks.Keys {
		if !k.MatchesFingerprint(spec) {
			left = append(left, k)
		} else {
			found = true
		}
	}
	if found {
		ks.Keys = left
	}
	return found
}

type KeyData struct {
	comments   []string
	pubkeyline string
	pubkey     ssh.PublicKey
	managed    bool
	shortname  string
}

// Read a single key from a reader.
// This may advance past the end of the key
func ReadKeyDataFromReader(rdr io.Reader) (*KeyData, error) {
	scanner := bufio.NewScanner(rdr)
	return ReadKeydataFromScanner(scanner)
}

// Read a single key from a scanner.
// Leave the scanner at the next line (or EOF)
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

// Parse the key from lines of data
// Expects 0 or more comment lines beginning with a #
// followed by a single line in authorized_keys format.
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

func (kd *KeyData) MatchesFingerprint(pk string) bool {
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

// Compare two KeyData instances.
// They compare as true iff the fingerprints of the keys match.
// Note that they explicitly *don't* care about options.
func (kd *KeyData) Equals(kd2 *KeyData) bool {
	if kd == nil || kd2 == nil {
		return false
	}
	return ssh.FingerprintSHA256(kd.pubkey) == ssh.FingerprintSHA256(kd2.pubkey)
}
