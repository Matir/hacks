package cache

import (
	"sync"
	"time"
)

type entry[V any] struct {
	value     V
	expiresAt time.Time
}

// Cache is a generic in-memory TTL cache safe for concurrent use.
type Cache[K comparable, V any] struct {
	mu    sync.Mutex
	items map[K]entry[V]
	ttl   time.Duration
}

// New creates a Cache with the given TTL for all entries.
func New[K comparable, V any](ttl time.Duration) *Cache[K, V] {
	return &Cache[K, V]{
		items: make(map[K]entry[V]),
		ttl:   ttl,
	}
}

// Get returns the cached value and true, or the zero value and false if the key
// is absent or expired.
func (c *Cache[K, V]) Get(key K) (V, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	e, ok := c.items[key]
	if !ok || time.Now().After(e.expiresAt) {
		delete(c.items, key)
		var zero V
		return zero, false
	}
	return e.value, true
}

// Set stores value under key, replacing any existing entry.
func (c *Cache[K, V]) Set(key K, value V) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items[key] = entry[V]{
		value:     value,
		expiresAt: time.Now().Add(c.ttl),
	}
}
