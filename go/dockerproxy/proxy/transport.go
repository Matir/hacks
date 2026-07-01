package proxy

import (
	"context"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/listener"
)

// NewTransport creates an http.Transport configured to dial the specified raw upstream address.
// Supports "unix:///path.sock", "tcp://host:port", or plain "http://host:port".
func NewTransport(upstreamAddr string) (*http.Transport, error) {
	network, addr, err := listener.ParseAddr(upstreamAddr)
	if err != nil {
		// Fallback for standard URL format passed directly (e.g. http://127.0.0.1:8080)
		if strings.HasPrefix(upstreamAddr, "http://") {
			network = "tcp"
			addr = strings.TrimPrefix(upstreamAddr, "http://")
		} else {
			return nil, err
		}
	}

	dialer := &net.Dialer{
		Timeout:   30 * time.Second,
		KeepAlive: 30 * time.Second,
	}

	return &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return dialer.DialContext(ctx, network, addr)
		},
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}, nil
}
