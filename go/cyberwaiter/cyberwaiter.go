package main

import (
  "archive/zip"
  "errors"
  "flag"
  "fmt"
  "io/fs"
  "log"
  "net/http"
  "os"
  "path/filepath"
  "strings"
  "time"

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
  forceUpdate bool
  noUpdate bool
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
  // Redirect on /
  if r.URL.Path == "/" {
    r.URL.Path = c.htmlName
  }
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
  for _, zf := range rdr.File {
    if !strings.HasSuffix(zf.FileHeader.Name, ".html") {
      continue
    }
    if !strings.HasPrefix(zf.FileHeader.Name, "CyberChef") {
      continue
    }
    c.htmlName = "/" + zf.FileHeader.Name
    log.Printf("Found index HTML file at %s", c.htmlName)
    break
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
  finfo, statErr := os.Stat(c.src)
  if c.noUpdate {
    if statErr != nil && errors.Is(statErr, fs.ErrNotExist) {
      log.Fatalf("Missing cyberchef.zip but updates disabled!")
    }
    return nil
  }
  needUpdate := c.forceUpdate
  if !needUpdate {
    if statErr != nil {
      // the stat failed
      needUpdate = true
    } else {
      modAgo := time.Now().Sub(finfo.ModTime())
      needUpdate = modAgo >= 30 * 24 * time.Hour
    }
  }
  if !needUpdate {
    return nil
  }
  log.Printf("Updating CyberChef source.")
  return UpdateCyberChef(c.src)
}

func WithListenAddress(addr string) CyberWaiterOption {
  return func (c *CyberWaiter) error {
    c.addr = addr
    return nil
  }
}

func WithForceUpdate() CyberWaiterOption {
  return func(c *CyberWaiter) error {
    c.forceUpdate = true
    return nil
  }
}

func WithNoUpdate() CyberWaiterOption {
  return func(c *CyberWaiter) error {
    c.noUpdate = true
    return nil
  }
}

func main() {
  addrFlag := flag.String("addr", DEFAULT_ADDR, "Address to serve on")
  forceUpdateFlag := flag.Bool("force-update", false, "Whether to force an update.")
  noUpdateFlag := flag.Bool("no-update", false, "Don't try to update.")

  opts := make([]CyberWaiterOption, 0)
  flag.Parse()
  if addrFlag != nil && *addrFlag != "" {
    // TODO: validate address
    opts = append(opts, WithListenAddress(*addrFlag))
  }
  if *forceUpdateFlag && *noUpdateFlag {
    log.Fatalf("Force update and no-update together doesn't make sense!")
  }
  if *forceUpdateFlag {
    opts = append(opts, WithForceUpdate())
  }
  if *noUpdateFlag {
    opts = append(opts, WithNoUpdate())
  }

  cw, err := NewCyberWaiter(opts...)
  if err != nil {
    panic(err)
  }
  if err := cw.RunServer(); err != nil {
    panic(err)
  }
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
