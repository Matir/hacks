package proxy

import (
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func TestNewTransportAndProxy_TCP(t *testing.T) {
	// Start mock upstream server on TCP
	mockBackend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Backend-Response", "hello")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("backend payload"))
	}))
	defer mockBackend.Close()

	// Create reverse proxy pointing to mock backend
	p, err := New(mockBackend.URL)
	if err != nil {
		t.Fatalf("unexpected error creating proxy: %v", err)
	}

	proxyServer := httptest.NewServer(p)
	defer proxyServer.Close()

	res, err := http.Get(proxyServer.URL + "/v1.43/containers/json")
	if err != nil {
		t.Fatalf("unexpected error requesting proxy server: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", res.StatusCode)
	}
	if val := res.Header.Get("X-Backend-Response"); val != "hello" {
		t.Errorf("expected header hello, got %q", val)
	}
	body, _ := io.ReadAll(res.Body)
	if string(body) != "backend payload" {
		t.Errorf("expected body 'backend payload', got %q", string(body))
	}
}

func TestNewTransport_Unix(t *testing.T) {
	tmpDir := t.TempDir()
	sockPath := filepath.Join(tmpDir, "backend.sock")

	ln, err := net.Listen("unix", sockPath)
	if err != nil {
		t.Fatalf("failed to listen unix socket: %v", err)
	}
	defer ln.Close()

	srv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusAccepted)
			_, _ = w.Write([]byte("unix ok"))
		}),
	}
	go func() { _ = srv.Serve(ln) }()
	defer srv.Close()

	transport, err := NewTransport("unix://" + sockPath)
	if err != nil {
		t.Fatalf("unexpected error creating unix transport: %v", err)
	}

	client := &http.Client{Transport: transport}
	res, err := client.Get("http://localhost/test")
	if err != nil {
		t.Fatalf("unix get error: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusAccepted {
		t.Errorf("expected 202, got %d", res.StatusCode)
	}
}
