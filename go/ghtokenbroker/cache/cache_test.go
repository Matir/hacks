package cache_test

import (
	"sync"
	"testing"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/cache"
)

func TestCache_SetGet(t *testing.T) {
	c := cache.New[string, int](time.Minute)
	c.Set("key", 42)

	got, ok := c.Get("key")
	if !ok {
		t.Fatal("expected hit, got miss")
	}
	if got != 42 {
		t.Errorf("got %d, want 42", got)
	}
}

func TestCache_Miss(t *testing.T) {
	c := cache.New[string, int](time.Minute)

	_, ok := c.Get("absent")
	if ok {
		t.Fatal("expected miss, got hit")
	}
}

func TestCache_Expiry(t *testing.T) {
	c := cache.New[string, int](10 * time.Millisecond)
	c.Set("key", 1)

	time.Sleep(20 * time.Millisecond)

	_, ok := c.Get("key")
	if ok {
		t.Fatal("expected expired entry to be a miss")
	}
}

func TestCache_Overwrite(t *testing.T) {
	c := cache.New[string, int](time.Minute)
	c.Set("key", 1)
	c.Set("key", 2)

	got, ok := c.Get("key")
	if !ok {
		t.Fatal("expected hit")
	}
	if got != 2 {
		t.Errorf("got %d, want 2", got)
	}
}

func TestCache_ConcurrentAccess(t *testing.T) {
	c := cache.New[int, int](time.Minute)
	const n = 100

	var wg sync.WaitGroup
	for i := range n {
		wg.Add(2)
		go func(i int) {
			defer wg.Done()
			c.Set(i, i*2)
		}(i)
		go func(i int) {
			defer wg.Done()
			c.Get(i)
		}(i)
	}
	wg.Wait()
}
