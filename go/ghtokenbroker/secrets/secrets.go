package secrets

import (
	"context"
	"fmt"
	"os"

	secretmanager "cloud.google.com/go/secretmanager/apiv1"
	"cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"

	"github.com/matir/hacks/go/ghtokenbroker/config"
)

// LoadPrivateKey retrieves the GitHub App RSA private key PEM bytes according
// to the source configured in cfg. Exactly one source must be active.
func LoadPrivateKey(ctx context.Context, cfg config.GitHubAppConfig) ([]byte, error) {
	switch {
	case cfg.PrivateKeyFile != "":
		return loadFromFile(cfg.PrivateKeyFile)
	case cfg.GCPSecretName != "":
		return loadFromGCP(ctx, cfg.GCPSecretName)
	default:
		// Should never happen if config validation ran, but fail closed.
		return nil, fmt.Errorf("secrets: no private key source configured")
	}
}

func loadFromFile(path string) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("secrets: read private key file %q: %w", path, err)
	}
	return data, nil
}

func loadFromGCP(ctx context.Context, name string) ([]byte, error) {
	client, err := secretmanager.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("secrets: create GCP Secret Manager client: %w", err)
	}
	defer client.Close()

	req := &secretmanagerpb.AccessSecretVersionRequest{Name: name}
	result, err := client.AccessSecretVersion(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("secrets: access GCP secret %q: %w", name, err)
	}
	return result.Payload.Data, nil
}
