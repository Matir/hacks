package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/matir/hacks/go/ghtokenbroker/audit"
	"github.com/matir/hacks/go/ghtokenbroker/config"
	githubclient "github.com/matir/hacks/go/ghtokenbroker/github"
	"github.com/matir/hacks/go/ghtokenbroker/policy"
	"github.com/matir/hacks/go/ghtokenbroker/secrets"
	"github.com/matir/hacks/go/ghtokenbroker/server"
)

func main() {
	configPath := flag.String("config", "config.toml", "path to TOML configuration file")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	privateKey, err := secrets.LoadPrivateKey(ctx, cfg.GitHubApp)
	if err != nil {
		log.Fatalf("failed to load GitHub App private key: %v", err)
	}

	ghClient, err := githubclient.New(cfg.GitHubApp, privateKey, cfg.Cache)
	if err != nil {
		log.Fatalf("failed to create GitHub client: %v", err)
	}

	policyEngine, err := policy.New(cfg.Agents)
	if err != nil {
		log.Fatalf("failed to initialise policy engine: %v", err)
	}

	auditor := audit.New(os.Stdout)

	srv := server.New(policyEngine, ghClient, auditor)

	log.Printf("starting ghtokenbroker (tcp=%q unix=%q)", cfg.Server.TCPAddr, cfg.Server.UnixSocket)
	if err := srv.ListenAndServe(ctx, cfg.Server.TCPAddr, cfg.Server.UnixSocket); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
