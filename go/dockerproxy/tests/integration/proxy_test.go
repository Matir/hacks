package integration

import (
	"context"
	"io"
	"net"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/listener"
	"github.com/Matir/hacks/go/dockerproxy/proxy"
)

func TestEndToEnd_TransparentProxying(t *testing.T) {
	backendSock := "/tmp/dp_be.sock"
	proxySock := "/tmp/dp_fe.sock"
	_ = os.Remove(backendSock)
	_ = os.Remove(proxySock)
	defer os.Remove(backendSock)
	defer os.Remove(proxySock)

	// 1. Setup mock backend Docker daemon listening on Unix socket
	backendLn, err := net.Listen("unix", backendSock)
	if err != nil {
		t.Fatalf("failed to listen on backend socket: %v", err)
	}
	defer backendLn.Close()

	backendSrv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`[{"Id":"container_1"}]`))
		}),
	}
	go func() { _ = backendSrv.Serve(backendLn) }()
	defer backendSrv.Close()

	// 2. Setup proxy listening on proxySock forwarding to backendSock
	proxyLn, err := listener.New("unix://" + proxySock)
	if err != nil {
		t.Fatalf("failed to create proxy listener: %v", err)
	}
	defer proxyLn.Close()

	p, err := proxy.New("unix://" + backendSock)
	if err != nil {
		t.Fatalf("failed to create proxy: %v", err)
	}

	proxySrv := &http.Server{Handler: p}
	go func() { _ = proxySrv.Serve(proxyLn) }()
	defer proxySrv.Close()

	// Give servers a brief moment to start
	time.Sleep(50 * time.Millisecond)

	// 3. Client requests via proxy Unix socket
	clientTransport := &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return net.Dial("unix", proxySock)
		},
	}
	client := &http.Client{Transport: clientTransport}

	res, err := client.Get("http://localhost/v1.43/containers/json")
	if err != nil {
		t.Fatalf("unexpected error requesting through proxy: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", res.StatusCode)
	}

	body, _ := io.ReadAll(res.Body)
	if string(body) != `[{"Id":"container_1"}]` {
		t.Errorf("unexpected body: %s", string(body))
	}
}
