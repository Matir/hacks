package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/config"
	"github.com/Matir/hacks/go/dockerproxy/listener"
	"github.com/Matir/hacks/go/dockerproxy/proxy"
	"github.com/Matir/hacks/go/dockerproxy/rules"
)

func TestEndToEnd_PolicyDenialEnforcement(t *testing.T) {
	backendSock := "/tmp/dp_rules_be.sock"
	proxySock := "/tmp/dp_rules_fe.sock"
	_ = os.Remove(backendSock)
	_ = os.Remove(proxySock)
	defer os.Remove(backendSock)
	defer os.Remove(proxySock)

	rulesContent := []byte(`
version: "1.0"
default_action: allow
rules:
  - id: deny-post-create
    methods: ["POST"]
    path_pattern: "^/v[\\d\\.]+/containers/create.*"
    action: deny
    message: "Container creation prohibited by ruleset."
`)
	rulesFile := filepath.Join(t.TempDir(), "rules.yaml")
	if err := os.WriteFile(rulesFile, rulesContent, 0600); err != nil {
		t.Fatalf("failed to write rules file: %v", err)
	}

	rs, err := config.LoadRuleset(rulesFile)
	if err != nil {
		t.Fatalf("failed to load ruleset: %v", err)
	}

	backendLn, err := net.Listen("unix", backendSock)
	if err != nil {
		t.Fatalf("failed to listen backend: %v", err)
	}
	defer backendLn.Close()

	backendSrv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("backend ok"))
		}),
	}
	go func() { _ = backendSrv.Serve(backendLn) }()
	defer backendSrv.Close()

	proxyLn, err := listener.New("unix://" + proxySock)
	if err != nil {
		t.Fatalf("failed to create proxy listener: %v", err)
	}
	defer proxyLn.Close()

	p, err := proxy.New("unix://" + backendSock)
	if err != nil {
		t.Fatalf("failed to create proxy: %v", err)
	}
	p.Use(proxy.RuleEvaluator(rs))

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

	res, err := client.Get("http://localhost/v1.43/containers/json")
	if err != nil {
		t.Fatalf("GET request failed: %v", err)
	}
	if res.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK on allowed GET, got %d", res.StatusCode)
	}
	res.Body.Close()

	res, err = client.Post("http://localhost/v1.43/containers/create", "application/json", bytes.NewReader([]byte("{}")))
	if err != nil {
		t.Fatalf("POST request failed: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusForbidden {
		t.Errorf("expected 403 Forbidden on denied POST, got %d", res.StatusCode)
	}

	body, _ := io.ReadAll(res.Body)
	if string(bytes.TrimSpace(body)) != "Container creation prohibited by ruleset." {
		t.Errorf("unexpected denial message: %q", string(body))
	}
}

func TestEndToEnd_SemanticPrivilegedDenial(t *testing.T) {
	backendSock := "/tmp/dp_sem_be.sock"
	proxySock := "/tmp/dp_sem_fe.sock"
	_ = os.Remove(backendSock)
	_ = os.Remove(proxySock)
	defer os.Remove(backendSock)
	defer os.Remove(proxySock)

	rulesContent := []byte(`
version: "1.0"
default_action: allow
rules:
  - id: block-privileged
    action: deny
    command_types: ["create"]
    container_create:
      privileged: true
    message: "Privileged mode prohibited."
`)
	rulesFile := filepath.Join(t.TempDir(), "rules_sem.yaml")
	_ = os.WriteFile(rulesFile, rulesContent, 0600)
	rs, err := config.LoadRuleset(rulesFile)
	if err != nil {
		t.Fatalf("failed to load semantic ruleset: %v", err)
	}

	backendLn, err := net.Listen("unix", backendSock)
	if err != nil {
		t.Fatalf("failed listening backend: %v", err)
	}
	defer backendLn.Close()

	backendSrv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusCreated)
			_, _ = w.Write([]byte(`{"Id":"new_container"}`))
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
	p.Use(proxy.RuleEvaluator(rs))

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

	// 1. Unprivileged container create -> 201 Created
	res, err := client.Post("http://localhost/v1.43/containers/create", "application/json", bytes.NewReader([]byte(`{"Image":"ubuntu","HostConfig":{"Privileged":false}}`)))
	if err != nil {
		t.Fatalf("unprivileged post failed: %v", err)
	}
	if res.StatusCode != http.StatusCreated {
		t.Errorf("expected 201 Created on unprivileged create, got %d", res.StatusCode)
	}
	res.Body.Close()

	// 2. Privileged container create -> 403 Forbidden
	res, err = client.Post("http://localhost/v1.43/containers/create", "application/json", bytes.NewReader([]byte(`{"Image":"ubuntu","HostConfig":{"Privileged":true}}`)))
	if err != nil {
		t.Fatalf("privileged post failed: %v", err)
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusForbidden {
		t.Errorf("expected 403 Forbidden on privileged create, got %d", res.StatusCode)
	}
	body, _ := io.ReadAll(res.Body)
	if string(bytes.TrimSpace(body)) != "Privileged mode prohibited." {
		t.Errorf("unexpected denial message: %q", string(body))
	}
}

func TestEndToEnd_SemanticListFiltering(t *testing.T) {
	backendSock := "/tmp/dp_flt_be.sock"
	proxySock := "/tmp/dp_flt_fe.sock"
	_ = os.Remove(backendSock)
	_ = os.Remove(proxySock)
	defer os.Remove(backendSock)
	defer os.Remove(proxySock)

	rulesContent := []byte(`
version: "1.0"
default_action: allow
rules:
  - id: filter-tenant-a
    action: filter
    command_types: ["list"]
    path_pattern: "^/v[\\d\\.]+/containers/json.*"
    response_filter:
      allowed_names: ["^tenant-a-.*"]
`)
	rulesFile := filepath.Join(t.TempDir(), "rules_flt.yaml")
	_ = os.WriteFile(rulesFile, rulesContent, 0600)
	rs, err := config.LoadRuleset(rulesFile)
	if err != nil {
		t.Fatalf("failed to load filter ruleset: %v", err)
	}

	backendLn, err := net.Listen("unix", backendSock)
	if err != nil {
		t.Fatalf("failed listening backend: %v", err)
	}
	defer backendLn.Close()

	mockContainers := []rules.ContainerSummary{
		{ID: "1", Names: []string{"/tenant-a-web"}},
		{ID: "2", Names: []string{"/tenant-b-db"}},
		{ID: "3", Names: []string{"/tenant-a-worker"}},
	}
	rawResp, _ := json.Marshal(mockContainers)

	backendSrv := &http.Server{
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write(rawResp)
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
	p.Use(proxy.RuleEvaluator(rs))

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

	res, err := client.Get("http://localhost/v1.43/containers/json")
	if err != nil {
		t.Fatalf("GET list failed: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", res.StatusCode)
	}

	body, _ := io.ReadAll(res.Body)
	var filtered []rules.ContainerSummary
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatalf("unmarshal filtered containers failed: %v", err)
	}

	if len(filtered) != 2 {
		t.Fatalf("expected 2 filtered containers, got %d", len(filtered))
	}
	if filtered[0].ID != "1" || filtered[1].ID != "3" {
		t.Errorf("unexpected container IDs retained: %+v", filtered)
	}
}
