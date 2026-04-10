// Package docker provides Docker container lifecycle management for OpenHands.
package docker

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/filters"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/api/types/mount"
	"github.com/docker/docker/client"
	"github.com/docker/go-connections/nat"
)

type contextKey string

const loggerKey contextKey = "logger"

func getLogger(ctx context.Context) *slog.Logger {
	if logger, ok := ctx.Value(loggerKey).(*slog.Logger); ok {
		return logger
	}
	return slog.Default()
}

// DockerManager defines the interface for managing OpenHands containers.
type DockerManager interface {
	// EnsureImage pulls the given image if it's not present locally.
	EnsureImage(ctx context.Context, imageName string) error
	// StopContainerByPort finds and terminates any container managed by HandHolder on the given port.
	StopContainerByPort(ctx context.Context, port int) error
	// StartContainer creates and runs a new OpenHands container.
	StartContainer(ctx context.Context, name string, port int, hostWorkspacePath string, imageName string, env map[string]string, disableSocketMount bool) error
	// GetContainerStatus returns the current status (e.g., "running") and workspace name for the container on a port.
	GetContainerStatus(ctx context.Context, port int) (string, string, error)
}

// Manager is the concrete implementation of DockerManager using the official Docker SDK.
type Manager struct {
	cli          client.APIClient
	dockerSocket string
}

// Ensure Manager implements DockerManager.
var _ DockerManager = (*Manager)(nil)

func parseSocketPath(s string) string {
	if strings.HasPrefix(s, "unix://") {
		return strings.TrimPrefix(s, "unix://")
	} else if strings.Contains(s, "://") {
		// Not a local unix socket
		return ""
	}
	return s
}

// NewManager creates a new DockerManager instance.
// If dockerSocket is provided, it connects to that socket instead of the default.
func NewManager(dockerSocket string) (*Manager, error) {
	opts := []client.Opt{client.FromEnv}
	var socketPath string

	if dockerSocket != "" {
		opts = append(opts, client.WithHost(dockerSocket))
		socketPath = parseSocketPath(dockerSocket)
	} else if envHost := os.Getenv("DOCKER_HOST"); envHost != "" {
		socketPath = parseSocketPath(envHost)
	} else {
		socketPath = "/var/run/docker.sock"
	}

	cli, err := client.NewClientWithOpts(opts...)
	if err != nil {
		return nil, err
	}
	return &Manager{cli: cli, dockerSocket: socketPath}, nil
}

// EnsureImage checks for the existence of an image and pulls it if missing.
func (m *Manager) EnsureImage(ctx context.Context, imageName string) error {
	logger := getLogger(ctx).With("image", imageName)
	_, _, err := m.cli.ImageInspectWithRaw(ctx, imageName)
	if err == nil {
		logger.Debug("Image already exists locally")
		return nil
	}

	logger.Info("Pulling image")
	out, err := m.cli.ImagePull(ctx, imageName, image.PullOptions{})
	if err != nil {
		logger.Error("Failed to pull image", "error", err)
		return fmt.Errorf("failed to pull image: %w", err)
	}
	defer out.Close()
	io.Copy(io.Discard, out) // Wait for pull to complete
	logger.Info("Image pull complete")
	return nil
}

// StopContainerByPort stops and removes a container named handholder-openhands-<port>.
func (m *Manager) StopContainerByPort(ctx context.Context, port int) error {
	name := fmt.Sprintf("handholder-openhands-%d", port)
	logger := getLogger(ctx).With("port", port, "container_name", name)

	// Try to find the container
	filter := filters.NewArgs()
	filter.Add("label", "managed-by=handholder")
	filter.Add("label", fmt.Sprintf("port=%d", port))
	containers, err := m.cli.ContainerList(ctx, container.ListOptions{All: true, Filters: filter})
	if err != nil {
		logger.Error("Failed to list containers", "error", err)
		return err
	}

	if len(containers) == 0 {
		logger.Debug("No container found to stop")
		return nil
	}

	for _, c := range containers {
		cLogger := logger.With("container_id", c.ID)
		cLogger.Info("Stopping and removing container")
		// Found it, stop and remove
		timeout := 5
		if err := m.cli.ContainerStop(ctx, c.ID, container.StopOptions{Timeout: &timeout}); err != nil {
			// If stop fails, try to force remove anyway
			cLogger.Warn("Failed to stop container, attempting force removal", "error", err)
		}
		if err := m.cli.ContainerRemove(ctx, c.ID, container.RemoveOptions{Force: true}); err != nil {
			cLogger.Error("Failed to remove container", "error", err)
			return fmt.Errorf("failed to remove container %s: %w", c.ID, err)
		}
		cLogger.Info("Container stopped and removed")
	}
	return nil
}

// StartContainer launches a new OpenHands container with the specified configuration.
func (m *Manager) StartContainer(ctx context.Context, name string, port int, hostWorkspacePath string, imageName string, env map[string]string, disableSocketMount bool) error {
	containerName := fmt.Sprintf("handholder-openhands-%d", port)
	logger := getLogger(ctx).With("workspace_id", name, "port", port, "image", imageName, "container_name", containerName)

	logger.Info("Creating container")

	config := m.buildContainerConfig(imageName, env, name, port)
	hostConfig := m.buildHostConfig(hostWorkspacePath, port, disableSocketMount)

	resp, err := m.cli.ContainerCreate(ctx, config, hostConfig, nil, nil, containerName)
	if err != nil {
		logger.Error("Failed to create container", "error", err)
		return fmt.Errorf("failed to create container: %w", err)
	}

	logger.Info("Starting container", "container_id", resp.ID)
	if err := m.cli.ContainerStart(ctx, resp.ID, container.StartOptions{}); err != nil {
		logger.Error("Failed to start container", "error", err, "container_id", resp.ID)
		return fmt.Errorf("failed to start container: %w", err)
	}

	logger.Info("Container started successfully", "container_id", resp.ID)
	return nil
}

func (m *Manager) buildContainerConfig(imageName string, env map[string]string, workspaceName string, port int) *container.Config {
	envSlice := make([]string, 0, len(env))
	for k, v := range env {
		envSlice = append(envSlice, fmt.Sprintf("%s=%s", k, v))
	}

	return &container.Config{
		Image: imageName,
		Env:   envSlice,
		ExposedPorts: nat.PortSet{
			"3000/tcp": struct{}{},
		},
		Labels: map[string]string{
			"managed-by": "handholder",
			"workspace":  workspaceName,
			"port":       fmt.Sprintf("%d", port),
		},
	}
}

func (m *Manager) buildHostConfig(hostWorkspacePath string, port int, disableSocketMount bool) *container.HostConfig {
	mounts := []mount.Mount{
		{
			Type:   mount.TypeBind,
			Source: hostWorkspacePath,
			Target: "/workspace",
		},
	}
	if homeDir, err := os.UserHomeDir(); err == nil {
		openhandsState := homeDir + "/.openhands-state"
		_ = os.MkdirAll(openhandsState, 0o700)
		mounts = append(mounts, mount.Mount{
			Type:   mount.TypeBind,
			Source: openhandsState,
			Target: "/.openhands-state",
		})
	}
	if !disableSocketMount && m.dockerSocket != "" {
		mounts = append(mounts, mount.Mount{
			Type:   mount.TypeBind,
			Source: m.dockerSocket,
			Target: "/var/run/docker.sock",
		})
	}

	return &container.HostConfig{
		PortBindings: nat.PortMap{
			"3000/tcp": []nat.PortBinding{
				{
					HostIP:   "127.0.0.1",
					HostPort: fmt.Sprintf("%d", port),
				},
			},
		},
		Mounts:     mounts,
		ExtraHosts: []string{"host.docker.internal:host-gateway"},
	}
}

// GetContainerStatus returns the current state (running, exited, etc.) and the workspace name for a given port.
func (m *Manager) GetContainerStatus(ctx context.Context, port int) (string, string, error) {
	logger := getLogger(ctx).With("port", port)
	filter := filters.NewArgs()
	filter.Add("label", "managed-by=handholder")
	filter.Add("label", fmt.Sprintf("port=%d", port))
	containers, err := m.cli.ContainerList(ctx, container.ListOptions{All: true, Filters: filter})
	if err != nil {
		logger.Error("Failed to list containers for status", "error", err)
		return "", "", err
	}

	if len(containers) == 0 {
		return "not running", "", nil
	}

	c := containers[0]
	return c.State, c.Labels["workspace"], nil
}
