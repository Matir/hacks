package main

import (
  "encoding/json"
  "errors"
  "fmt"
  "io"
  "io/fs"
  "log"
  "net/http"
  "os"
  "strings"
)

const (
  CYBERCHEF_LATEST = "https://api.github.com/repos/GCHQ/CyberChef/releases/latest"
  USER_AGENT = "cyberwaiter/0.0.1"
)

type ReleaseAsset struct {
  Name string `json:"name"`
  Size int64 `json:"size"`
  URL string `json:"browser_download_url"`
}

type ReleaseInfo struct {
  Assets []ReleaseAsset `json:"assets"`
  TagName string `json:"tag_name"`
}

func UpdateCyberChef(dest string) error {
  return UpdateCyberChefFromRelease(CYBERCHEF_LATEST, dest)
}

func UpdateCyberChefFromRelease(src, dest string) error {
  rinfo, err := fetchReleaseInfo(src)
  if err != nil {
    return err
  }
  ctag, err := getCurrentTag(dest)
  if err != nil {
    return err
  }
  if ctag == rinfo.TagName {
    // Nothing to do here
    return nil
  }
  // Download to temp file
  tempName := dest + ".tmp"
  for _, a := range rinfo.Assets {
    if strings.HasSuffix(a.Name, ".zip") {
      if err := updaterDownloadFile(a.URL, tempName); err != nil {
        return err
      }
      break
    }
  }
  // Rename and update tag
  if err := os.Rename(tempName, dest); err != nil {
    return err
  }
  if err := os.WriteFile(getTagFilename(dest), []byte(rinfo.TagName), 0644); err != nil {
    return err
  }
  return nil
}

func getTagFilename(dest string) string {
  return dest + ".tag"
}

func getCurrentTag(dest string) (string, error) {
  fname := getTagFilename(dest)
  if buf, err := os.ReadFile(fname); err != nil {
    if errors.Is(err, fs.ErrNotExist) {
      return "", nil
    }
    return "", err
  } else {
    tag := string(buf)
    return strings.TrimSpace(tag), nil
  }
}

func fetchReleaseInfo(src string) (*ReleaseInfo, error) {
  client := http.Client{}
  req, err := http.NewRequest(http.MethodGet, src, nil)
  if err != nil {
    return nil, err
  }
  req.Header.Set("Accept", "application/json")
  req.Header.Set("User-Agent", USER_AGENT)
  resp, err := client.Do(req)
  if err != nil {
    return nil, err
  }
  defer resp.Body.Close()
  if resp.StatusCode != http.StatusOK {
    return nil, fmt.Errorf("Error retrieving info, got code %d", resp.StatusCode)
  }
  dec := json.NewDecoder(resp.Body)
  var info ReleaseInfo
  if err := dec.Decode(&info); err != nil {
    return nil, err
  }
  return &info, nil
}

func updaterDownloadFile(src, dest string) error {
  log.Printf("Downloading %v", src)
  client := http.Client{}
  req, err := http.NewRequest(http.MethodGet, src, nil)
  if err != nil {
    return err
  }
  req.Header.Set("User-Agent", USER_AGENT)
  resp, err := client.Do(req)
  if err != nil {
    return err
  }
  defer resp.Body.Close()
  if resp.StatusCode != http.StatusOK {
    return fmt.Errorf("Error retrieving file, got code %d", resp.StatusCode)
  }
  fp, err := os.Create(dest)
  if err != nil {
    return err
  }
  defer fp.Close()
  if err := fp.Chmod(0644); err != nil {
    return err
  }
  if _, err := io.Copy(fp, resp.Body); err != nil {
    return err
  }
  return nil
}
