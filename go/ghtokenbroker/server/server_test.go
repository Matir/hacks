package server_test

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/audit"
	"github.com/matir/hacks/go/ghtokenbroker/config"
	githubclient "github.com/matir/hacks/go/ghtokenbroker/github"
	"github.com/matir/hacks/go/ghtokenbroker/policy"
	"github.com/matir/hacks/go/ghtokenbroker/server"

	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
)

// fakeGitHubServer returns an httptest.Server that stubs out the two GitHub
// endpoints the client uses during a token request.
func fakeGitHubServer(t *testing.T) *httptest.Server {
	t.Helper()
	expiry := time.Now().Add(time.Hour).UTC().Format(time.RFC3339)
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/repos/org/repo1/installation", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintln(w, `{"id": 1}`)
	})
	mux.HandleFunc("/api/v3/app/installations/1/access_tokens", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"token":"ghs_testtoken","expires_at":%q}`+"\n", expiry)
	})
	return httptest.NewServer(mux)
}

func generatePEM(t *testing.T) []byte {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate RSA key: %v", err)
	}
	return pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PRIVATE KEY",
		Bytes: x509.MarshalPKCS1PrivateKey(key),
	})
}

func buildServer(t *testing.T) (*server.Server, *httptest.Server) {
	t.Helper()

	ghSrv := fakeGitHubServer(t)

	agents := []config.AgentConfig{
		{
			ID:           "agent1",
			APIKey:       "valid-key",
			AllowedRepos: []string{"org/repo1"},
			MaxPermissions: config.PermissionSet{
				"contents": "write",
				"metadata": "read",
			},
		},
	}

	policyEngine, err := policy.New(agents)
	if err != nil {
		t.Fatalf("policy.New: %v", err)
	}

	pemKey := generatePEM(t)
	cfg := config.GitHubAppConfig{AppID: 1}
	ghClient, err := githubclient.NewWithBaseURL(cfg, pemKey, config.CacheConfig{}, ghSrv.URL+"/")
	if err != nil {
		t.Fatalf("NewWithBaseURL: %v", err)
	}

	auditor := audit.New(io.Discard)
	srv := server.New(policyEngine, ghClient, auditor)
	return srv, ghSrv
}

func doRequest(t *testing.T, srv *server.Server, method, path, authHeader, body string) *httptest.ResponseRecorder {
	t.Helper()
	var bodyReader io.Reader
	if body != "" {
		bodyReader = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, bodyReader)
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rr := httptest.NewRecorder()
	srv.ServeHTTP(rr, req)
	return rr
}

func tokenBody(repo string, perms map[string]string) string {
	b, _ := json.Marshal(map[string]interface{}{
		"repo":                  repo,
		"requested_permissions": perms,
		"task_id":               "t1",
	})
	return string(b)
}

func TestHandleToken_MissingAuth(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	rr := doRequest(t, srv, http.MethodPost, "/v1/token", "", tokenBody("org/repo1", map[string]string{"contents": "read"}))
	if rr.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rr.Code)
	}
}

func TestHandleToken_InvalidKey(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	rr := doRequest(t, srv, http.MethodPost, "/v1/token", "Bearer wrong-key", tokenBody("org/repo1", map[string]string{"contents": "read"}))
	if rr.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rr.Code)
	}
}

func TestHandleToken_DisallowedRepo(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	rr := doRequest(t, srv, http.MethodPost, "/v1/token", "Bearer valid-key", tokenBody("org/other", map[string]string{"contents": "read"}))
	if rr.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rr.Code)
	}
}

func TestHandleToken_ElevatedPermission(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	// agent1 has max contents=write; requesting administration=write (not in max set) should fail.
	rr := doRequest(t, srv, http.MethodPost, "/v1/token", "Bearer valid-key", tokenBody("org/repo1", map[string]string{"administration": "write"}))
	if rr.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rr.Code)
	}
}

func TestHandleToken_Success(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	rr := doRequest(t, srv, http.MethodPost, "/v1/token", "Bearer valid-key", tokenBody("org/repo1", map[string]string{"contents": "read", "metadata": "read"}))
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body: %s", rr.Code, rr.Body.String())
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if resp["token"] == "" || resp["token"] == nil {
		t.Error("response missing token")
	}
	if resp["expires_at"] == nil {
		t.Error("response missing expires_at")
	}
	if resp["repo"] != "org/repo1" {
		t.Errorf("repo = %v, want org/repo1", resp["repo"])
	}
}

func TestHandleToken_CorrelationID(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	req := httptest.NewRequest(http.MethodPost, "/v1/token", bytes.NewBufferString(tokenBody("org/repo1", map[string]string{"contents": "read"})))
	req.Header.Set("Authorization", "Bearer valid-key")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Request-ID", "my-corr-id")
	rr := httptest.NewRecorder()
	srv.ServeHTTP(rr, req)

	if rr.Header().Get("X-Request-ID") != "my-corr-id" {
		t.Errorf("X-Request-ID = %q, want my-corr-id", rr.Header().Get("X-Request-ID"))
	}
}

func TestHandleHealth(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	rr := doRequest(t, srv, http.MethodGet, "/healthz", "", "")
	if rr.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rr.Code)
	}
	var resp map[string]interface{}
	_ = json.NewDecoder(rr.Body).Decode(&resp)
	if resp["status"] != "ok" {
		t.Errorf("status = %v, want ok", resp["status"])
	}
}

func TestHandleToken_MalformedBody(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	req := httptest.NewRequest(http.MethodPost, "/v1/token", strings.NewReader("not-json"))
	req.Header.Set("Authorization", "Bearer valid-key")
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	srv.ServeHTTP(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rr.Code)
	}
}

// Ensure Server is used in a real test scenario (not just httptest).
func TestListenAndServe_AtLeastOneListener(t *testing.T) {
	srv, ghSrv := buildServer(t)
	defer ghSrv.Close()

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancel immediately

	err := srv.ListenAndServe(ctx, "", "")
	if err == nil {
		t.Fatal("expected error when no listeners configured")
	}
}
