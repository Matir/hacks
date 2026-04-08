package github_test

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/config"
	githubclient "github.com/matir/hacks/go/ghtokenbroker/github"
)

// generateTestKey produces a minimal RSA private key suitable for signing JWTs
// in tests (not for production use).
func generateTestKey(t *testing.T) []byte {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate RSA key: %v", err)
	}
	der := x509.MarshalPKCS1PrivateKey(key)
	return pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: der})
}

func newTestClient(t *testing.T, mux *http.ServeMux) (*githubclient.Client, *httptest.Server) {
	t.Helper()
	ts := httptest.NewServer(mux)

	pemKey := generateTestKey(t)
	cfg := config.GitHubAppConfig{AppID: 1}
	cacheCfg := config.CacheConfig{}

	client, err := githubclient.NewWithBaseURL(cfg, pemKey, cacheCfg, ts.URL+"/")
	if err != nil {
		ts.Close()
		t.Fatalf("NewWithBaseURL: %v", err)
	}
	return client, ts
}

func TestGetInstallationID_Success(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/repos/org/repo/installation", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintln(w, `{"id": 42}`)
	})

	client, ts := newTestClient(t, mux)
	defer ts.Close()

	id, err := client.GetInstallationID(context.Background(), "org", "repo")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if id != 42 {
		t.Errorf("id = %d, want 42", id)
	}
}

func TestGetInstallationID_Cached(t *testing.T) {
	calls := 0
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/repos/org/repo/installation", func(w http.ResponseWriter, r *http.Request) {
		calls++
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintln(w, `{"id": 99}`)
	})

	client, ts := newTestClient(t, mux)
	defer ts.Close()

	for range 3 {
		_, err := client.GetInstallationID(context.Background(), "org", "repo")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
	}
	if calls != 1 {
		t.Errorf("GitHub API called %d times, want 1 (should be cached)", calls)
	}
}

func TestGetInstallationID_APIError(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/repos/org/repo/installation", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"message":"Not Found"}`, http.StatusNotFound)
	})

	client, ts := newTestClient(t, mux)
	defer ts.Close()

	_, err := client.GetInstallationID(context.Background(), "org", "repo")
	if err == nil {
		t.Fatal("expected error for 404 response")
	}
}

func TestMintToken_Success(t *testing.T) {
	expiry := time.Now().Add(time.Hour).UTC().Format(time.RFC3339)
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/app/installations/42/access_tokens", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]interface{}
		_ = json.NewDecoder(r.Body).Decode(&body)
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"token":"ghs_test","expires_at":%q}`, expiry)
	})

	client, ts := newTestClient(t, mux)
	defer ts.Close()

	perms := config.PermissionSet{"contents": "read"}
	token, err := client.MintToken(context.Background(), 42, "org", "repo", perms)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if token.GetToken() != "ghs_test" {
		t.Errorf("token = %q, want ghs_test", token.GetToken())
	}
}

func TestMintToken_APIError(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v3/app/installations/42/access_tokens", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"message":"Forbidden"}`, http.StatusForbidden)
	})

	client, ts := newTestClient(t, mux)
	defer ts.Close()

	_, err := client.MintToken(context.Background(), 42, "org", "repo", config.PermissionSet{"contents": "read"})
	if err == nil {
		t.Fatal("expected error for 403 response")
	}
}

func TestSplitRepo(t *testing.T) {
	tests := []struct {
		input     string
		wantOwner string
		wantRepo  string
		wantErr   bool
	}{
		{"org/repo", "org", "repo", false},
		{"user/my-repo", "user", "my-repo", false},
		{"noslash", "", "", true},
		{"/norepo", "", "", true},
		{"noowner/", "", "", true},
		{"", "", "", true},
	}
	for _, tt := range tests {
		owner, repo, err := githubclient.SplitRepo(tt.input)
		if (err != nil) != tt.wantErr {
			t.Errorf("SplitRepo(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			continue
		}
		if err == nil && (owner != tt.wantOwner || repo != tt.wantRepo) {
			t.Errorf("SplitRepo(%q) = (%q, %q), want (%q, %q)", tt.input, owner, repo, tt.wantOwner, tt.wantRepo)
		}
	}
}
