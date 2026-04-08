package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/BurntSushi/toml"
)

// ---------------------------------------------------------------------------
// Configuration types
// ---------------------------------------------------------------------------

// clientConfig holds values decoded from ~/.ghtok.
type clientConfig struct {
	APIKey             string   `toml:"api_key"`
	Server             string   `toml:"server"`
	DefaultPermissions []string `toml:"default_permissions"`
}

// resolvedConfig is the final merged configuration used by all modes.
type resolvedConfig struct {
	APIKey             string
	Server             string
	DefaultPermissions map[string]string // permission name → "read"|"write"
}

// defaultPermissions is the fallback when no default_permissions are configured.
var defaultPermissions = map[string]string{
	"contents": "write",
	"metadata": "read",
}

// ---------------------------------------------------------------------------
// Wire protocol types (mirrored from server/server.go — not imported)
// ---------------------------------------------------------------------------

type tokenRequest struct {
	Repo                 string            `json:"repo"`
	RequestedPermissions map[string]string `json:"requested_permissions"`
	TaskID               string            `json:"task_id,omitempty"`
	Purpose              string            `json:"purpose,omitempty"`
}

type tokenResponse struct {
	Token              string            `json:"token"`
	ExpiresAt          time.Time         `json:"expires_at"`
	Repo               string            `json:"repo"`
	GrantedPermissions map[string]string `json:"granted_permissions"`
}

type errResponse struct {
	Error string `json:"error"`
}

// ---------------------------------------------------------------------------
// Mode detection
// ---------------------------------------------------------------------------

type mode int

const (
	modeDirect mode = iota
	modeGHWrapper
	modeCredHelper
)

// detectMode inspects os.Args and returns the operating mode plus the
// remaining args (with any consumed leading positional arg removed).
func detectMode() (mode, []string) {
	args := os.Args[1:]

	base := filepath.Base(os.Args[0])
	switch base {
	case "gh":
		return modeGHWrapper, args
	case "git-credential-ghtok":
		return modeCredHelper, args
	}

	if len(args) > 0 {
		switch args[0] {
		case "gh":
			return modeGHWrapper, args[1:]
		case "get", "store", "erase":
			return modeCredHelper, args
		}
	}

	return modeDirect, args
}

// ---------------------------------------------------------------------------
// Config loading
// ---------------------------------------------------------------------------

// loadDotfile reads ~/.ghtok if it exists. A missing file is not an error.
func loadDotfile() (*clientConfig, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("could not determine home directory: %w", err)
	}
	path := filepath.Join(home, ".ghtok")
	var cfg clientConfig
	_, err = toml.DecodeFile(path, &cfg)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("reading ~/.ghtok: %w", err)
	}
	return &cfg, nil
}

// parsePermissions parses a slice of "name:level" strings into a map.
func parsePermissions(perms []string) (map[string]string, error) {
	m := make(map[string]string, len(perms))
	for _, p := range perms {
		parts := strings.SplitN(p, ":", 2)
		if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
			return nil, fmt.Errorf("invalid permission %q: expected name:level", p)
		}
		m[parts[0]] = parts[1]
	}
	return m, nil
}

// loadConfig merges configuration from all sources (last wins):
// dotfile → env vars → flags.
func loadConfig(dotfile *clientConfig, apiKeyFlag, serverFlag string) (*resolvedConfig, error) {
	cfg := &resolvedConfig{}

	// 1. Dotfile
	if dotfile != nil {
		cfg.APIKey = dotfile.APIKey
		cfg.Server = dotfile.Server
		if len(dotfile.DefaultPermissions) > 0 {
			perms, err := parsePermissions(dotfile.DefaultPermissions)
			if err != nil {
				return nil, fmt.Errorf("~/.ghtok default_permissions: %w", err)
			}
			cfg.DefaultPermissions = perms
		}
	}

	// 2. Environment variables
	if v := os.Getenv("GHTOK_API_KEY"); v != "" {
		cfg.APIKey = v
	}
	if v := os.Getenv("GHTOK_SERVER"); v != "" {
		cfg.Server = v
	}

	// 3. Flags
	if apiKeyFlag != "" {
		cfg.APIKey = apiKeyFlag
	}
	if serverFlag != "" {
		cfg.Server = serverFlag
	}

	// Apply default permissions fallback.
	if len(cfg.DefaultPermissions) == 0 {
		cfg.DefaultPermissions = defaultPermissions
	}

	return cfg, nil
}

// ---------------------------------------------------------------------------
// HTTP client construction
// ---------------------------------------------------------------------------

// newHTTPClient parses the server address and returns an http.Client configured
// for the appropriate transport, plus the base URL to use for requests.
//
// Supported formats:
//
//	tcp://host:port   → plain TCP HTTP
//	unix:///abs/path  → Unix domain socket HTTP
func newHTTPClient(server string) (*http.Client, string, error) {
	u, err := url.Parse(server)
	if err != nil {
		return nil, "", fmt.Errorf("invalid server address %q: %w", server, err)
	}

	switch u.Scheme {
	case "tcp":
		host := u.Host
		client := &http.Client{Timeout: 30 * time.Second}
		return client, "http://" + host, nil

	case "unix":
		socketPath := u.Path
		if socketPath == "" {
			return nil, "", fmt.Errorf("unix socket path is empty in %q", server)
		}
		client := &http.Client{
			Timeout:   30 * time.Second,
			Transport: unixTransport(socketPath),
		}
		return client, "http://unix", nil

	default:
		return nil, "", fmt.Errorf("unsupported server scheme %q (use tcp:// or unix://)", u.Scheme)
	}
}

// unixTransport returns an http.RoundTripper that dials a Unix domain socket.
func unixTransport(socketPath string) http.RoundTripper {
	return &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, "unix", socketPath)
		},
	}
}

// ---------------------------------------------------------------------------
// Broker client
// ---------------------------------------------------------------------------

type brokerClient struct {
	httpClient *http.Client
	baseURL    string
	apiKey     string
}

// newBrokerClient constructs a brokerClient from a resolvedConfig.
func newBrokerClient(cfg *resolvedConfig) (*brokerClient, error) {
	if cfg.Server == "" {
		return nil, fmt.Errorf("server address is not configured (set GHTOK_SERVER, --server, or server in ~/.ghtok)")
	}
	if cfg.APIKey == "" {
		return nil, fmt.Errorf("API key is not configured (set GHTOK_API_KEY, --api-key, or api_key in ~/.ghtok)")
	}
	hc, base, err := newHTTPClient(cfg.Server)
	if err != nil {
		return nil, err
	}
	return &brokerClient{httpClient: hc, baseURL: base, apiKey: cfg.APIKey}, nil
}

// RequestToken calls POST /v1/token and returns the response.
func (c *brokerClient) RequestToken(ctx context.Context, req tokenRequest) (*tokenResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("encoding request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/v1/token", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("building request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("contacting broker: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var errResp errResponse
		_ = json.NewDecoder(resp.Body).Decode(&errResp)
		if errResp.Error != "" {
			return nil, fmt.Errorf("broker error (HTTP %d): %s", resp.StatusCode, errResp.Error)
		}
		return nil, fmt.Errorf("broker returned HTTP %d", resp.StatusCode)
	}

	var tok tokenResponse
	if err := json.NewDecoder(resp.Body).Decode(&tok); err != nil {
		return nil, fmt.Errorf("decoding response: %w", err)
	}
	return &tok, nil
}

// ---------------------------------------------------------------------------
// Git repo detection
// ---------------------------------------------------------------------------

// repoFromGitRemote runs "git remote get-url origin" in dir (cwd if "")
// and parses the output to return "owner/repo" for GitHub remotes.
func repoFromGitRemote(dir string) (string, error) {
	args := []string{"remote", "get-url", "origin"}
	if dir != "" {
		args = append([]string{"-C", dir}, args...)
	}
	out, err := exec.Command("git", args...).Output()
	if err != nil {
		return "", fmt.Errorf("git remote get-url origin: %w", err)
	}
	remote := strings.TrimSpace(string(out))
	return parseGitHubRemote(remote)
}

// parseGitHubRemote parses an SSH or HTTPS GitHub remote URL into "owner/repo".
func parseGitHubRemote(remote string) (string, error) {
	// SSH: git@github.com:owner/repo.git
	if strings.HasPrefix(remote, "git@github.com:") {
		path := strings.TrimPrefix(remote, "git@github.com:")
		path = strings.TrimSuffix(path, ".git")
		if !strings.Contains(path, "/") {
			return "", fmt.Errorf("unexpected SSH remote format: %q", remote)
		}
		return path, nil
	}

	// HTTPS: https://github.com/owner/repo[.git]
	u, err := url.Parse(remote)
	if err != nil {
		return "", fmt.Errorf("parsing remote URL %q: %w", remote, err)
	}
	if u.Host != "github.com" {
		return "", fmt.Errorf("not a github.com remote: %q", remote)
	}
	path := strings.TrimPrefix(u.Path, "/")
	path = strings.TrimSuffix(path, ".git")
	if !strings.Contains(path, "/") {
		return "", fmt.Errorf("unexpected HTTPS remote path: %q", remote)
	}
	return path, nil
}

// ---------------------------------------------------------------------------
// Find next gh binary
// ---------------------------------------------------------------------------

// findNextGH returns the absolute path of the first "gh" binary in PATH
// that is not the current executable.
func findNextGH() (string, error) {
	self, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("cannot determine current executable: %w", err)
	}
	selfReal, err := filepath.EvalSymlinks(self)
	if err != nil {
		selfReal = self
	}

	pathEnv := os.Getenv("PATH")
	for _, dir := range filepath.SplitList(pathEnv) {
		if dir == "" {
			continue
		}
		candidate := filepath.Join(dir, "gh")
		info, err := os.Stat(candidate)
		if err != nil {
			continue
		}
		if info.IsDir() {
			continue
		}
		if info.Mode()&0o111 == 0 {
			continue // not executable
		}
		candidateReal, err := filepath.EvalSymlinks(candidate)
		if err != nil {
			candidateReal = candidate
		}
		if candidateReal == selfReal {
			continue // this is us
		}
		return candidate, nil
	}
	return "", fmt.Errorf("no gh binary found in PATH (other than this tool)")
}

// ---------------------------------------------------------------------------
// Mode: direct token request
// ---------------------------------------------------------------------------

func runDirect(cfg *resolvedConfig, args []string) error {
	fs := flag.NewFlagSet("ghtok", flag.ContinueOnError)
	repo := fs.String("repo", "", "GitHub repository in owner/repo format (required)")
	permsFlag := fs.String("permissions", "", "Comma-separated permissions, e.g. contents:write,metadata:read")
	taskID := fs.String("task-id", "", "Optional task/correlation ID")
	purpose := fs.String("purpose", "", "Optional human-readable purpose")

	if err := fs.Parse(args); err != nil {
		return err
	}

	if *repo == "" {
		fs.Usage()
		return fmt.Errorf("--repo is required")
	}

	perms := cfg.DefaultPermissions
	if *permsFlag != "" {
		parsed, err := parsePermissions(strings.Split(*permsFlag, ","))
		if err != nil {
			return err
		}
		perms = parsed
	}

	client, err := newBrokerClient(cfg)
	if err != nil {
		return err
	}

	tok, err := client.RequestToken(context.Background(), tokenRequest{
		Repo:                 *repo,
		RequestedPermissions: perms,
		TaskID:               *taskID,
		Purpose:              *purpose,
	})
	if err != nil {
		return err
	}

	fmt.Println(tok.Token)
	return nil
}

// ---------------------------------------------------------------------------
// Mode: gh wrapper
// ---------------------------------------------------------------------------

func runGHWrapper(cfg *resolvedConfig, args []string) error {
	ghPath, err := findNextGH()
	if err != nil {
		return err
	}

	repo, err := repoFromGitRemote("")
	if err != nil {
		return fmt.Errorf("could not detect GitHub repository from git remote: %w", err)
	}

	client, err := newBrokerClient(cfg)
	if err != nil {
		return err
	}

	tok, err := client.RequestToken(context.Background(), tokenRequest{
		Repo:                 repo,
		RequestedPermissions: cfg.DefaultPermissions,
		Purpose:              "gh wrapper",
	})
	if err != nil {
		return err
	}

	// Inject GH_TOKEN into the environment and replace this process with gh.
	env := injectEnv(os.Environ(), "GH_TOKEN", tok.Token)
	argv := append([]string{"gh"}, args...)
	return syscall.Exec(ghPath, argv, env)
}

// injectEnv returns a copy of environ with key=value set (replacing any
// existing entry for key).
func injectEnv(environ []string, key, value string) []string {
	prefix := key + "="
	result := make([]string, 0, len(environ)+1)
	for _, e := range environ {
		if !strings.HasPrefix(e, prefix) {
			result = append(result, e)
		}
	}
	return append(result, prefix+value)
}

// ---------------------------------------------------------------------------
// Mode: git credential helper
// ---------------------------------------------------------------------------

func runCredHelper(cfg *resolvedConfig, args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("git credential helper requires an operation argument (get, store, erase)")
	}
	op := args[0]

	switch op {
	case "store", "erase":
		// Drain stdin and do nothing — tokens are ephemeral.
		_, _ = io.Copy(io.Discard, os.Stdin)
		return nil

	case "get":
		return runCredGet(cfg)

	default:
		return fmt.Errorf("unknown credential operation %q", op)
	}
}

// runCredGet implements the git credential "get" operation.
func runCredGet(cfg *resolvedConfig) error {
	fields, err := parseGitCredentialInput(os.Stdin)
	if err != nil {
		return fmt.Errorf("reading git credential input: %w", err)
	}

	// Only handle github.com; let git fall through for other hosts.
	host := fields["host"]
	if host != "" && host != "github.com" {
		return nil
	}

	// Derive owner/repo from the path field, or fall back to git remote.
	var repo string
	if path, ok := fields["path"]; ok && path != "" {
		repo = strings.TrimPrefix(path, "/")
		repo = strings.TrimSuffix(repo, ".git")
		if !strings.Contains(repo, "/") {
			return fmt.Errorf("cannot parse repository from git credential path %q", path)
		}
	} else {
		repo, err = repoFromGitRemote("")
		if err != nil {
			return fmt.Errorf("could not detect GitHub repository: %w", err)
		}
	}

	client, err := newBrokerClient(cfg)
	if err != nil {
		return err
	}

	tok, err := client.RequestToken(context.Background(), tokenRequest{
		Repo:                 repo,
		RequestedPermissions: cfg.DefaultPermissions,
		Purpose:              "git credential helper",
	})
	if err != nil {
		return err
	}

	fmt.Fprintf(os.Stdout, "protocol=https\nhost=github.com\nusername=x-access-token\npassword=%s\n\n", tok.Token)
	return nil
}

// parseGitCredentialInput reads key=value pairs from r until EOF or a blank line.
func parseGitCredentialInput(r io.Reader) (map[string]string, error) {
	fields := make(map[string]string)
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			break
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			fields[parts[0]] = parts[1]
		}
	}
	return fields, scanner.Err()
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	log.SetFlags(0)
	log.SetPrefix("ghtok: ")

	m, remaining := detectMode()

	// Parse global flags from the remaining args.
	globalFlags := flag.NewFlagSet("ghtok", flag.ContinueOnError)
	apiKeyFlag := globalFlags.String("api-key", "", "API key for the token broker")
	serverFlag := globalFlags.String("server", "", "Broker server address (tcp://host:port or unix:///path)")

	// For gh wrapper and cred helper modes, stop at first non-flag so that
	// arguments intended for gh/git are not consumed.
	if m == modeGHWrapper || m == modeCredHelper {
		globalFlags.SetOutput(io.Discard) // suppress flag errors on unknown flags
		_ = globalFlags.Parse(remaining)
		remaining = globalFlags.Args()
	} else {
		if err := globalFlags.Parse(remaining); err != nil {
			log.Fatalf("%v", err)
		}
		remaining = globalFlags.Args()
	}

	dotfile, err := loadDotfile()
	if err != nil {
		log.Fatalf("%v", err)
	}

	cfg, err := loadConfig(dotfile, *apiKeyFlag, *serverFlag)
	if err != nil {
		log.Fatalf("%v", err)
	}

	switch m {
	case modeDirect:
		if err := runDirect(cfg, remaining); err != nil {
			log.Fatalf("%v", err)
		}
	case modeGHWrapper:
		if err := runGHWrapper(cfg, remaining); err != nil {
			log.Fatalf("%v", err)
		}
	case modeCredHelper:
		if err := runCredHelper(cfg, remaining); err != nil {
			log.Fatalf("%v", err)
		}
	}
}
