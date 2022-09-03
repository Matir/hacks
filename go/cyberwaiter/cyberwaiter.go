package main

import (
  "net/http"
  "archive/zip"
  "os"
  "path/filepath"
  "io/fs"
  "fmt"
  "log"

  "github.com/urfave/negroni"
)

const (
  DEFAULT_ADDR = "127.0.0.1:7890"
  DEFAULT_FNAME = "cyberchef.zip"
)

type CyberWaiter struct {
  zipReader *zip.Reader
  zipHandler http.Handler
  fp *os.File
  addr string
  src string
  htmlName string
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
  rw := negroni.NewResponseWriter(w)
  c.zipHandler.ServeHTTP(rw, r)
  c.logRequest(rw, r)
}

func (c *CyberWaiter) logRequest(rw negroni.ResponseWriter, r *http.Request) {
  log.Printf("[%s] %s %s %d %s %d", r.RemoteAddr, r.Method, r.URL.String(), rw.Status(), http.StatusText(rw.Status()), rw.Size())
}

func (c *CyberWaiter) RunServer() error {
  if err := c.maybeUpdate(); err != nil {
    return err
  }
  if err := c.prepareZipServer(); err != nil {
    return err
  }
  defer c.fp.Close()
  log.Printf("Starting server on %s", c.addr)
  return http.ListenAndServe(c.addr, c)
}

func (c *CyberWaiter) prepareZipServer() error {
  fp, err := os.Open(c.src)
  if err != nil {
    return err
  }
  fi, err := fp.Stat()
  if err != nil {
    fp.Close()
    return err
  }
  rdr, err := zip.NewReader(fp, fi.Size())
  if err != nil {
    fp.Close()
    return err
  }
  c.zipReader = rdr
  c.fp = fp
  c.zipHandler = http.FileServer(http.FS(rdr))
  return nil
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
  log.Printf("Updating CyberChef source.")
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
  if err := cw.RunServer(); err != nil {
    panic(err)
  }
}
