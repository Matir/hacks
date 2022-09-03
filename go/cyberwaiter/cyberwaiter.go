package main

import (
  "net/http"
  "archive/zip"
  "os"
  "path/filepath"
  "io/fs"
  "fmt"
)

const (
  DEFAULT_ADDR = "127.0.0.1:7890"
  DEFAULT_FNAME = "cyberchef.zip"
)

type CyberWaiter struct {
  zipReader *zip.Reader
  addr string
  src string
}

type CyberWaiterOption func(*CyberWaiter) error

func NewCyberWaiter(opts ...CyberWaiterOption) (*CyberWaiter, error) {
  rv := &CyberWaiter{
    addr: DEFAULT_ADDR,
  }
  for _, o := range opts {
    if err := o(rv); err != nil {
      return nil, fmt.Errorf("Error setting option in NewCyberWaiter: %w", err)
    }
  }
  if rv.src == "" {
    if cacheDir, err := getAppCacheDir(); err != nil {
      return nil, fmt.Errorf("Error getting cache dir: %w", err)
    } else {
      rv.src = filepath.Join(cacheDir, DEFAULT_FNAME)
    }
  }
  if err := rv.mkCacheDir(); err != nil {
    return nil, fmt.Errorf("Error creating cache dir: %w", err)
  }
  return rv, nil
}

func (c *CyberWaiter) ServeHTTP(w http.ResponseWriter, r *http.Request) {
}

func (c *CyberWaiter) mkCacheDir() error {
  dirname := filepath.Dir(c.src)
  if err := os.MkdirAll(dirname, fs.FileMode(0755)); err != nil {
    return err
  }
  return nil
}

func (c *CyberWaiter) maybeUpdate() error {
  // TODO: make this conditional, etc.
  return UpdateCyberChef(c.src)
}

func getAppCacheDir() (string, error) {
  cacheDir := os.Getenv("XDG_CACHE_HOME")
  if cacheDir == "" {
    homeDir, err := os.UserHomeDir()
    if err != nil {
      return "", err
    }
    cacheDir = filepath.Join(homeDir, ".cache")
  }
  rv := filepath.Join(cacheDir, "cyberwaiter")
  return rv, nil
}

func main() {
  cw, err := NewCyberWaiter()
  if err != nil {
    panic(err)
  }
  if err := cw.maybeUpdate(); err != nil {
    panic(err)
  }
}
