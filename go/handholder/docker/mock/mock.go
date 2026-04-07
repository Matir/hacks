package mock

import (
	"context"
	"io"
	"strings"
	"sync"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/api/types/network"
	ocispec "github.com/opencontainers/image-spec/specs-go/v1"
	"github.com/docker/docker/client"
)

// FakeDockerClient implements client.CommonAPIClient (the base for APIClient)
// We only implement the methods used by the Manager.
type FakeDockerClient struct {
	client.APIClient
	mu         sync.Mutex
	Containers map[string]*container.Config
	Images     map[string]bool
}

// NewFakeDockerClient creates a new FakeDockerClient instance.
func NewFakeDockerClient() *FakeDockerClient {
	return &FakeDockerClient{
		Containers: make(map[string]*container.Config),
		Images:     make(map[string]bool),
	}
}

// ImageInspectWithRaw emulates checking for image existence.
func (f *FakeDockerClient) ImageInspectWithRaw(ctx context.Context, imageID string) (types.ImageInspect, []byte, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if _, ok := f.Images[imageID]; ok {
		return types.ImageInspect{}, nil, nil
	}
	return types.ImageInspect{}, nil, dockerError("not found")
}

// ImagePull emulates pulling an image.
func (f *FakeDockerClient) ImagePull(ctx context.Context, ref string, options image.PullOptions) (io.ReadCloser, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.Images[ref] = true
	return io.NopCloser(strings.NewReader("pulled")), nil
}

// ContainerList emulates listing containers by filter.
func (f *FakeDockerClient) ContainerList(ctx context.Context, options container.ListOptions) ([]types.Container, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	
	nameFilter := options.Filters.Get("name")
	var result []types.Container
	for name, config := range f.Containers {
		match := false
		if len(nameFilter) == 0 {
			match = true
		} else {
			for _, nf := range nameFilter {
				if strings.Contains(name, nf) {
					match = true
					break
				}
			}
		}
		
		if match {
			result = append(result, types.Container{
				ID:     name + "-id",
				Names:  []string{"/" + name},
				State:  "running",
				Labels: config.Labels,
			})
		}
	}
	return result, nil
}

// ContainerCreate emulates creating a container.
func (f *FakeDockerClient) ContainerCreate(ctx context.Context, config *container.Config, hostConfig *container.HostConfig, networkingConfig *network.NetworkingConfig, platform *ocispec.Platform, containerName string) (container.CreateResponse, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	
	// Strip leading slash if present
	containerName = strings.TrimPrefix(containerName, "/")
	f.Containers[containerName] = config
	return container.CreateResponse{ID: containerName + "-id"}, nil
}

// ContainerStart emulates starting a container.
func (f *FakeDockerClient) ContainerStart(ctx context.Context, containerID string, options container.StartOptions) error {
	return nil
}

// ContainerStop emulates stopping a container.
func (f *FakeDockerClient) ContainerStop(ctx context.Context, containerID string, options container.StopOptions) error {
	return nil
}

// ContainerRemove emulates removing a container.
func (f *FakeDockerClient) ContainerRemove(ctx context.Context, containerID string, options container.RemoveOptions) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	name := strings.TrimSuffix(containerID, "-id")
	delete(f.Containers, name)
	return nil
}

type fakeError string
func (e fakeError) Error() string { return string(e) }
func dockerError(msg string) error { return fakeError(msg) }

// --- Fake Manager ---

// FakeManager provides a mock implementation of the DockerManager interface.
type FakeManager struct {
	mu         sync.Mutex
	Workspaces map[int]string
	Ensured    map[string]bool
}

// NewFakeManager creates a new FakeManager instance.
func NewFakeManager() *FakeManager {
	return &FakeManager{
		Workspaces: make(map[int]string),
		Ensured:    make(map[string]bool),
	}
}

// EnsureImage marks the image as ensured.
func (f *FakeManager) EnsureImage(ctx context.Context, imageName string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.Ensured[imageName] = true
	return nil
}

// StopContainerByPort removes the workspace from the specified port.
func (f *FakeManager) StopContainerByPort(ctx context.Context, port int) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	delete(f.Workspaces, port)
	return nil
}

// StartContainer adds a workspace to the specified port.
func (f *FakeManager) StartContainer(ctx context.Context, name string, port int, hostWorkspacePath string, imageName string, env map[string]string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.Workspaces[port] = name
	return nil
}

// GetContainerStatus returns the status and workspace for the given port.
func (f *FakeManager) GetContainerStatus(ctx context.Context, port int) (string, string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if name, ok := f.Workspaces[port]; ok {
		return "running", name, nil
	}
	return "not running", "", nil
}
