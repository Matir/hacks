// Package listener provides unified socket creation and shutdown for Unix and TCP endpoints.
package listener

import (
	"net"
	"os"
	"strings"

	"github.com/Matir/hacks/go/dockerproxy/config"
)

// Listener wraps net.Listener to ensure proper cleanup of Unix socket files upon closure.
type Listener struct {
	net.Listener
	network  string
	sockPath string
}

// ParseAddr parses raw address strings (e.g. "tcp://127.0.0.1:8080" or "unix:///path.sock")
// into Go net network and address strings.
func ParseAddr(rawInput string) (string, string, error) {
	if strings.HasPrefix(rawInput, "tcp://") {
		return "tcp", strings.TrimPrefix(rawInput, "tcp://"), nil
	}
	if strings.HasPrefix(rawInput, "unix://") {
		return "unix", strings.TrimPrefix(rawInput, "unix://"), nil
	}
	return "", "", config.ErrUnsupportedSocket
}

// New creates and starts a net.Listener on the specified raw endpoint address.
// Supports "tcp://addr:port" and "unix:///path/to/socket".
func New(rawAddr string) (*Listener, error) {
	network, addr, err := ParseAddr(rawAddr)
	if err != nil {
		return nil, err
	}

	if network == "unix" {
		// Remove existing stale socket file if present
		_ = os.Remove(addr)
	}

	ln, err := net.Listen(network, addr)
	if err != nil {
		return nil, err
	}

	l := &Listener{
		Listener: ln,
		network:  network,
	}
	if network == "unix" {
		l.sockPath = addr
	}

	return l, nil
}

// Close closes the underlying listener and cleans up Unix socket file if needed.
func (l *Listener) Close() error {
	err := l.Listener.Close()
	if l.network == "unix" && l.sockPath != "" {
		_ = os.Remove(l.sockPath)
	}
	return err
}
