package integration

import (
	"bufio"
	"context"
	"encoding/json"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/listener"
	"github.com/Matir/hacks/go/dockerproxy/proxy"
	"github.com/Matir/hacks/go/dockerproxy/recorder"
)

func TestEndToEnd_TrafficRecording(t *testing.T) {
	backendSock := "/tmp/dp_rec_be.sock"
	proxySock := "/tmp/dp_rec_fe.sock"
	_ = os.Remove(backendSock)
	_ = os.Remove(proxySock)
	defer os.Remove(backendSock)
	defer os.Remove(proxySock)

	recFile := filepath.Join(t.TempDir(), "traffic.jsonl")

	backendLn, err := net.Listen("unix", backendSock)
	if err != nil {
		t.Fatalf("failed listening backend: %v", err)
	}
	defer backendLn.Close()

	backendSrv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("recorded response body"))
		}),
	}
	go func() { _ = backendSrv.Serve(backendLn) }()
	defer backendSrv.Close()

	proxyLn, err := listener.New("unix://" + proxySock)
	if err != nil {
		t.Fatalf("failed proxy listener: %v", err)
	}
	defer proxyLn.Close()

	p, err := proxy.New("unix://" + backendSock)
	if err != nil {
		t.Fatalf("failed proxy: %v", err)
	}

	recWriter, err := recorder.NewWriter(recFile)
	if err != nil {
		t.Fatalf("failed recorder writer: %v", err)
	}
	defer recWriter.Close()
	p.Use(recorder.Middleware(recWriter))

	proxySrv := &http.Server{Handler: p}
	go func() { _ = proxySrv.Serve(proxyLn) }()
	defer proxySrv.Close()

	time.Sleep(50 * time.Millisecond)

	clientTransport := &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return net.Dial("unix", proxySock)
		},
	}
	client := &http.Client{Transport: clientTransport}

	res, err := client.Get("http://localhost/v1.43/version")
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	res.Body.Close()

	// Give recorder background write a brief moment
	time.Sleep(20 * time.Millisecond)

	f, err := os.Open(recFile)
	if err != nil {
		t.Fatalf("failed opening recording file: %v", err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	if !scanner.Scan() {
		t.Fatalf("expected at least 1 recorded line, got EOF")
	}

	var rec recorder.TrafficRecord
	if err := json.Unmarshal(scanner.Bytes(), &rec); err != nil {
		t.Fatalf("unmarshal record failed: %v", err)
	}

	if rec.Method != "GET" || rec.URI != "/v1.43/version" {
		t.Errorf("unexpected method/uri in record: %s %s", rec.Method, rec.URI)
	}
	if rec.StatusCode != 200 || rec.Outcome != "allowed" {
		t.Errorf("unexpected status/outcome: %d %s", rec.StatusCode, rec.Outcome)
	}
	if rec.ResponseBody != "recorded response body" {
		t.Errorf("unexpected response body: %q", rec.ResponseBody)
	}
}
