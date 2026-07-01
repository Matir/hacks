// Package proxy implements transparent HTTP reverse proxying and connection hijacking for Docker API requests.
package proxy

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"time"
)

type sessionKeyType struct{}

var sessionKey = sessionKeyType{}

// ProxySession represents an active transaction between a client and the target daemon.
type ProxySession struct {
	ID           string
	ClientAddr   string
	UpstreamAddr string
	StartTime    time.Time
	IsUpgraded   bool
}

// NewSession creates a new ProxySession with a random 16-character hex ID.
func NewSession(clientAddr, upstreamAddr string) *ProxySession {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return &ProxySession{
		ID:           hex.EncodeToString(b),
		ClientAddr:   clientAddr,
		UpstreamAddr: upstreamAddr,
		StartTime:    time.Now().UTC(),
	}
}

// WithSession returns a new context carrying the provided ProxySession.
func WithSession(ctx context.Context, session *ProxySession) context.Context {
	return context.WithValue(ctx, sessionKey, session)
}

// FromContext extracts a ProxySession from the context, if present.
func FromContext(ctx context.Context) (*ProxySession, bool) {
	s, ok := ctx.Value(sessionKey).(*ProxySession)
	return s, ok
}
