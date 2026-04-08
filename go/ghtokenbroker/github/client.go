package github

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/bradleyfalzon/ghinstallation/v2"
	gh "github.com/google/go-github/v84/github"

	"github.com/matir/hacks/go/ghtokenbroker/cache"
	"github.com/matir/hacks/go/ghtokenbroker/config"
)

// Client wraps the GitHub App API to look up installation IDs and mint
// short-lived installation tokens.
type Client struct {
	ghClient *gh.Client
	appTrans *ghinstallation.AppsTransport
	cache    *cache.Cache[string, int64]
}

// New creates a Client using the provided app ID and PEM-encoded private key.
// installationTTL controls how long installation ID lookups are cached.
func New(cfg config.GitHubAppConfig, privateKey []byte, cacheCfg config.CacheConfig) (*Client, error) {
	return newClient(cfg, privateKey, cacheCfg, "")
}

// NewWithBaseURL creates a Client that targets baseURL instead of api.github.com.
// Intended for use in tests with an httptest.Server.
func NewWithBaseURL(cfg config.GitHubAppConfig, privateKey []byte, cacheCfg config.CacheConfig, baseURL string) (*Client, error) {
	return newClient(cfg, privateKey, cacheCfg, baseURL)
}

func newClient(cfg config.GitHubAppConfig, privateKey []byte, cacheCfg config.CacheConfig, baseURL string) (*Client, error) {
	ttl := cacheCfg.InstallationTTL.Duration
	if ttl == 0 {
		ttl = 5 * 60 * 1_000_000_000 // 5 minutes default
	}

	appTrans, err := ghinstallation.NewAppsTransport(http.DefaultTransport, cfg.AppID, privateKey)
	if err != nil {
		return nil, fmt.Errorf("github: create app transport: %w", err)
	}

	var ghc *gh.Client
	if baseURL != "" {
		ghc, err = gh.NewClient(&http.Client{Transport: appTrans}).WithEnterpriseURLs(baseURL, baseURL)
		if err != nil {
			return nil, fmt.Errorf("github: set base URL: %w", err)
		}
	} else {
		ghc = gh.NewClient(&http.Client{Transport: appTrans})
	}

	return &Client{
		ghClient: ghc,
		appTrans: appTrans,
		cache:    cache.New[string, int64](ttl),
	}, nil
}

// GetInstallationID returns the GitHub App installation ID for owner/repo.
// Results are cached according to the configured TTL.
func (c *Client) GetInstallationID(ctx context.Context, owner, repo string) (int64, error) {
	cacheKey := owner + "/" + repo
	if id, ok := c.cache.Get(cacheKey); ok {
		return id, nil
	}

	install, _, err := c.ghClient.Apps.FindRepositoryInstallation(ctx, owner, repo)
	if err != nil {
		return 0, fmt.Errorf("github: find installation for %s/%s: %w", owner, repo, err)
	}

	id := install.GetID()
	c.cache.Set(cacheKey, id)
	return id, nil
}

// MintToken requests a new installation token scoped to a single repository
// with the given permissions. CreateInstallationToken is an App-level API, so
// it uses the App JWT client (c.ghClient), not an installation-scoped client.
func (c *Client) MintToken(ctx context.Context, installationID int64, owner, repo string, perms config.PermissionSet) (*gh.InstallationToken, error) {
	ghPerms := permissionSetToGH(perms)
	opts := &gh.InstallationTokenOptions{
		Repositories: []string{repo},
		Permissions:  ghPerms,
	}

	token, _, err := c.ghClient.Apps.CreateInstallationToken(ctx, installationID, opts)
	if err != nil {
		return nil, fmt.Errorf("github: create installation token for %s/%s (install %d): %w", owner, repo, installationID, err)
	}
	return token, nil
}

// splitRepo splits "owner/repo" into its two parts, returning an error if the
// format is invalid.
func SplitRepo(fullName string) (owner, repo string, err error) {
	parts := strings.SplitN(fullName, "/", 2)
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("github: invalid repo format %q, expected owner/repo", fullName)
	}
	return parts[0], parts[1], nil
}

// permissionSetToGH converts a config.PermissionSet to the GitHub API type.
func permissionSetToGH(ps config.PermissionSet) *gh.InstallationPermissions {
	perms := &gh.InstallationPermissions{}
	for name, level := range ps {
		l := level // local copy for pointer
		switch name {
		case "contents":
			perms.Contents = &l
		case "pull_requests":
			perms.PullRequests = &l
		case "issues":
			perms.Issues = &l
		case "metadata":
			perms.Metadata = &l
		case "actions":
			perms.Actions = &l
		case "checks":
			perms.Checks = &l
		case "deployments":
			perms.Deployments = &l
		case "environments":
			perms.Environments = &l
		case "pages":
			perms.Pages = &l
		case "statuses":
			perms.Statuses = &l
		}
	}
	return perms
}
