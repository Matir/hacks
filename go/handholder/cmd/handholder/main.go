package main

import (
	"context"
	"flag"
	"log"
	"log/slog"

	"github.com/matir/hacks/go/handholder/config"
	"github.com/matir/hacks/go/handholder/docker"
	"github.com/matir/hacks/go/handholder/web"
)

func main() {
	configPath := flag.String("config", "handholder.toml", "path to config file")

	// Handholder override flags
	bindAddr := flag.String("bind-address", "", "IP address to bind to (overrides config)")
	port := flag.Int("port", 0, "port for the HandHolder service (overrides config)")
	logging := flag.String("logging", "", "logging output destination (overrides config)")
	logFormat := flag.String("logformat", "", "logging format: text or json (overrides config)")
	dockerSocket := flag.String("docker-socket", "", "Docker socket path (overrides config)")
	trustedProxies := flag.String("trusted-proxies", "", "comma-separated list of trusted proxy IPs/CIDRs (overrides config)")
	disableSocketMount := flag.Bool("disable-socket-mount", false, "disable mounting Docker socket in containers (overrides config)")
	preloadImages := flag.Bool("preload-images", true, "preload Docker images on startup (overrides config)")

	flag.Parse()

	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("Error loading config: %v", err)
	}

	// Apply overrides for flags that were explicitly set
	overrides := config.Overrides{
		BindAddress:    *bindAddr,
		Port:           *port,
		Logging:        *logging,
		LogFormat:      *logFormat,
		DockerSocket:   *dockerSocket,
		TrustedProxies: *trustedProxies,
	}
	flag.Visit(func(f *flag.Flag) {
		switch f.Name {
		case "disable-socket-mount":
			overrides.DisableSocketMount = disableSocketMount
		case "preload-images":
			overrides.PreloadImages = preloadImages
		}
	})
	cfg.ApplyOverrides(overrides)

	handler, err := config.GetLogHandler(cfg.HandHolder.Logging, cfg.HandHolder.LogFormat)
	if err != nil {
		log.Fatalf("Error setting up logging: %v", err)
	}
	slog.SetDefault(slog.New(handler))

	dockerMgr, err := docker.NewManager(cfg.HandHolder.DockerSocket)
	if err != nil {
		slog.Error("Error initializing Docker manager", "error", err)
		return
	}

	if cfg.HandHolder.PreloadImages {
		go preloadDockerImages(dockerMgr, cfg)
	}

	server := web.NewServer(cfg, dockerMgr)
	if err := server.Start(); err != nil {
		slog.Error("Server error", "error", err)
		return
	}
}
func preloadDockerImages(dockerMgr docker.DockerManager, cfg *config.Config) {
	images := make(map[string]struct{})
	if cfg.Defaults.Image != "" {
		images[config.EnsureTag(cfg.Defaults.Image)] = struct{}{}
	}
	if cfg.Defaults.SandboxBaseImage != "" {
		images[config.EnsureTag(cfg.Defaults.SandboxBaseImage)] = struct{}{}
	}

	for _, ws := range cfg.Workspaces {
		if ws.Image != "" {
			images[config.EnsureTag(ws.Image)] = struct{}{}
		}
		if ws.SandboxBaseImage != "" {
			images[config.EnsureTag(ws.SandboxBaseImage)] = struct{}{}
		}
	}

	ctx := context.Background()
	for img := range images {
		slog.Info("Preloading image", "image", img)
		if err := dockerMgr.EnsureImage(ctx, img); err != nil {
			slog.Error("Failed to preload image", "image", img, "error", err)
		}
	}
}
