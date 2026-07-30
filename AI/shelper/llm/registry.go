package llm

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// Registry manages the collection of LLM provider implementations.
type Registry struct {
	mu        sync.RWMutex
	providers map[string]Provider
}

// NewRegistry instantiates a new empty Provider registry.
func NewRegistry() *Registry {
	return &Registry{
		providers: make(map[string]Provider),
	}
}

// Register adds a provider instance to the registry map.
func (r *Registry) Register(p Provider) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.providers[p.Name()] = p
}

// Get retrieves a provider implementation by name, wrapped with retry resilience.
func (r *Registry) Get(name string) (Provider, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	p, ok := r.providers[name]
	if !ok {
		return nil, fmt.Errorf("unsupported provider %q", name)
	}
	// Wrap with retry resiliency (3 total attempts)
	return &RetryingProvider{base: p, maxRetries: 2}, nil
}

// RetryingProvider wraps a base Provider and adds retry logic for transient errors.
type RetryingProvider struct {
	base       Provider
	maxRetries int
}

// Name returns the underlying provider's name.
func (rp *RetryingProvider) Name() string {
	return rp.base.Name()
}

// Generate retries generation with exponential backoff on failure.
func (rp *RetryingProvider) Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error) {
	var lastErr error
	for attempt := 0; attempt <= rp.maxRetries; attempt++ {
		// Respect context cancellation
		if err := ctx.Err(); err != nil {
			return nil, err
		}

		if attempt > 0 {
			// Exponential backoff: 100ms, 200ms
			sleepDur := time.Duration(attempt) * 100 * time.Millisecond
			log.Printf("[INFO] Retrying provider %s in %v (attempt %d/%d)...", rp.base.Name(), sleepDur, attempt+1, rp.maxRetries+1)
			time.Sleep(sleepDur)
		}

		resp, err := rp.base.Generate(ctx, req)
		if err == nil {
			return resp, nil
		}
		lastErr = err
		log.Printf("[WARN] Generation attempt %d failed for provider %s: %v", attempt+1, rp.base.Name(), err)
	}
	return nil, fmt.Errorf("provider %s failed after %d attempts: %w", rp.base.Name(), rp.maxRetries+1, lastErr)
}
