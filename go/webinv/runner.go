package main

import (
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/tebeka/selenium"
)

const (
	CHROME_PATH_DEFAULT       = "/opt/google/chrome-beta/google-chrome"
	CHROMEDRIVER_PATH_DEFAULT = "./chromedriver"
	CHROMEDRIVER_PORT_DEFAULT = "8123"
	CHROME_PATH_VAR           = "CHROME_PATH"
	CHROMEDRIVER_PATH_VAR     = "CHROMEDRIVER_PATH"
	CHROMEDRIVER_PORT_VAR     = "CHROMEDRIVER_PORT"
)

type WebWorker struct {
	svc     *selenium.Service
	wd      *selenium.WebDriver
	handler PageHandler
}

type PageHandler interface {
	HandlePage(*selenium.WebDriver) error
}

func NewWebWorker(svc *selenium.Service, port int, handler PageHandler) (*WebWorker, error) {
	ww := &WebWorker{
		svc:     svc,
		handler: handler,
	}
	caps := selenium.Capabilities{"browserName": "chrome"}
	wd, err := selenium.NewRemote(caps, fmt.Sprintf("http://localhost:%s/wd/hub", port))
	if err != nil {
		return nil, err
	}
	return ww, nil
}

func (ww *WebWorker) RunPage(url string) error {
	log.Printf("Loading page: %s", url)
	defer log.Printf("Finished page: %s", url)
	if err := ww.wd.Get(url); err != nil {
		return err
	}
	if ww.handler != nil {
		return ww.handler.HandlePage(ww.wd)
	}
	return nil
}

func GetenvDefault(key, def string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return def
}

func GetPort() int {
	portStr := GetenvDefault(CHROMEDRIVER_PORT_VAR, CHROMEDRIVER_PORT_DEFAULT)
	if v, err := strconv.Atoi(portStr); err != nil {
		panic(err)
	} else {
		return v
	}
}
