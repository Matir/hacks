// Package docker provides Docker container lifecycle management for OpenHands.
package docker

import (
	"context"
	"fmt"
	"io"

	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/filters"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/api/types/mount"
	"github.com/docker/docker/client"
	"github.com/docker/go-connections/nat"
)

// DockerManager defines the interface for managing OpenHands containers.
type DockerManager interface {
	// EnsureImage pulls the given image if it's not present locally.
	EnsureImage(ctx context.Context, imageName string) error
	// StopContainerByPort finds and terminates any container managed by HandHolder on the given port.
	StopContainerByPort(ctx context.Context, port int) error
	// StartContainer creates and runs a new OpenHands container.
	StartContainer(ctx context.Context, name string, port int, hostWorkspacePath string, imageName string, env map[string]string) error
	// GetContainerStatus returns the current status (e.g., "running") and workspace name for the container on a port.
	GetContainerStatus(ctx context.Context, port int) (string, string, error)
}

// Manager is the concrete implementation of DockerManager using the official Docker SDK.
type Manager struct {
	cli client.APIClient
}

// Ensure Manager implements DockerManager.
var _ DockerManager = (*Manager)(nil)

// NewManager creates a new DockerManager instance.
// If dockerSocket is provided, it connects to that socket instead of the default.
func NewManager(dockerSocket string) (*Manager, error) {
	opts := []client.Opt{client.FromEnv}
	if dockerSocket != "" {
		opts = append(opts, client.WithHost(dockerSocket))
	}
	cli, err := client.NewClientWithOpts(opts...)
	if err != nil {
		return nil, err
	}
	return &Manager{cli: cli}, nil
}

// EnsureImage checks for the existence of an image and pulls it if missing.
func (m *Manager) EnsureImage(ctx context.Context, imageName string) error {
	_, _, err := m.cli.ImageInspectWithRaw(ctx, imageName)
	if err == nil {
		return nil
	}

	out, err := m.cli.ImagePull(ctx, imageName, image.PullOptions{})
	if err != nil {
		return fmt.Errorf("failed to pull image: %w", err)
	}
	defer out.Close()
	io.Copy(io.Discard, out) // Wait for pull to complete
	return nil
}

// StopContainerByPort stops and removes a container named handholder-openhands-<port>.
func (m *Manager) StopContainerByPort(ctx context.Context, port int) error {
	name := fmt.Sprintf("handholder-openhands-%d", port)
	
	// Try to find the container
	filter := filters.NewArgs()
	filter.Add("name", name)
	containers, err := m.cli.ContainerList(ctx, container.ListOptions{All: true, Filters: filter})
	if err != nil {
		return err
	}

	for _, c := range containers {
		// Found it, stop and remove
		timeout := 5
		if err := m.cli.ContainerStop(ctx, c.ID, container.StopOptions{Timeout: &timeout}); err != nil {
			// If stop fails, try to force remove anyway
			fmt.Printf("Warning: failed to stop container %s: %v\n", c.ID, err)
		}
		if err := m.cli.ContainerRemove(ctx, c.ID, container.RemoveOptions{Force: true}); err != nil {
			return fmt.Errorf("failed to remove container %s: %w", c.ID, err)
		}
	}
	return nil
}

// StartContainer launches a new OpenHands container with the specified configuration.
func (m *Manager) StartContainer(ctx context.Context, name string, port int, hostWorkspacePath string, imageName string, env map[string]string) error {
	containerName := fmt.Sprintf("handholder-openhands-%d", port)
	
	// Prepare environment
	envSlice := make([]string, 0, len(env))
	for k, v := range env {
		envSlice = append(envSlice, fmt.Sprintf("%s=%s", k, v))
	}

	// Prepare config
	config := &container.Config{
		Image: imageName,
		Env:   envSlice,
		ExposedPorts: nat.PortSet{
			"3000/tcp": struct{}{},
		},
		Labels: map[string]string{
			"managed-by": "handholder",
			"workspace":  name,
			"port":       fmt.Sprintf("%d", port),
		},
	}

	// Prepare host config
	hostConfig := &container.HostConfig{
		PortBindings: nat.PortMap{
			"3000/tcp": []nat.PortBinding{
				{
					HostIP:   "127.0.0.1",
					HostPort: fmt.Sprintf("%d", port),
				},
			},
		},
		Mounts: []mount.Mount{
			{
				Type:   mount.TypeBind,
				Source: hostWorkspacePath,
				Target: "/opt/workspace_base",
			},
		},
	}

	resp, err := m.cli.ContainerCreate(ctx, config, hostConfig, nil, nil, containerName)
	if err != nil {
		return fmt.Errorf("failed to create container: %w", err)
	}

	if err := m.cli.ContainerStart(ctx, resp.ID, container.StartOptions{}); err != nil {
		return fmt.Errorf("failed to start container: %w", err)
	}

	return nil
}

// GetContainerStatus returns the current state (running, exited, etc.) and the workspace name for a given port.
func (m *Manager) GetContainerStatus(ctx context.Context, port int) (string, string, error) {
	name := fmt.Sprintf("handholder-openhands-%d", port)
	filter := filters.NewArgs()
	filter.Add("name", name)
	containers, err := m.cli.ContainerList(ctx, container.ListOptions{All: true, Filters: filter})
	if err != nil {
		return "", "", err
	}

	if len(containers) == 0 {
		return "not running", "", nil
	}

	c := containers[0]
	return c.State, c.Labels["workspace"], nil
}
