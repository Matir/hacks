package proxy

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/listener"
)

// isUpgradeRequest checks if the request is asking for an HTTP connection upgrade or TCP hijack.
func isUpgradeRequest(r *http.Request) bool {
	connHeader := strings.ToLower(r.Header.Get("Connection"))
	upgradeHeader := strings.ToLower(r.Header.Get("Upgrade"))
	return strings.Contains(connHeader, "upgrade") || upgradeHeader != ""
}

// handleHijack intercepts upgraded connections (e.g. docker exec -it) and proxies raw socket streams.
func handleHijack(w http.ResponseWriter, r *http.Request, upstreamAddr string) error {
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		return fmt.Errorf("response writer does not support hijacking")
	}

	network, addr, err := listener.ParseAddr(upstreamAddr)
	if err != nil {
		if strings.HasPrefix(upstreamAddr, "http://") {
			network = "tcp"
			addr = strings.TrimPrefix(upstreamAddr, "http://")
		} else {
			return err
		}
	}

	upstreamConn, err := net.DialTimeout(network, addr, 10*time.Second)
	if err != nil {
		http.Error(w, fmt.Sprintf("upstream connection failed: %v", err), http.StatusBadGateway)
		return err
	}
	defer func() { _ = upstreamConn.Close() }()

	// Write original upgrade request directly to upstream connection
	if err := r.Write(upstreamConn); err != nil {
		http.Error(w, fmt.Sprintf("writing upgrade request failed: %v", err), http.StatusBadGateway)
		return err
	}

	clientConn, _, err := hijacker.Hijack()
	if err != nil {
		return fmt.Errorf("client connection hijack failed: %v", err)
	}
	defer func() { _ = clientConn.Close() }()

	if session, ok := FromContext(r.Context()); ok {
		session.IsUpgraded = true
	}

	// Bidirectional raw copying
	errChan := make(chan error, 2)
	go func() {
		_, err := io.Copy(upstreamConn, clientConn)
		errChan <- err
	}()
	go func() {
		_, err := io.Copy(clientConn, upstreamConn)
		errChan <- err
	}()

	<-errChan
	return nil
}
