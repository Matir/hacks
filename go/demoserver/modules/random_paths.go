package modules

import (
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/matir/hacks/go/demoserver/words"
)

type RandomPathsModule struct {
	files []string
}

func NewRandomPathsModule() *RandomPathsModule {
	rpm := &RandomPathsModule{}
	rpm.Setup()
	return rpm
}

func (rpm *RandomPathsModule) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("%s path: %s", rpm, r.URL)
	path := r.URL.Path
	if path[0] == '/' {
		path = path[1:]
	}
	if idx := strings.Index(path, "/"); idx != -1 {
		path = path[idx+1:]
	} else {
		// Rooted path
		w.WriteHeader(http.StatusOK)
		return
	}
	log.Printf("%s path trimmed: %s", rpm, path)
	for _, f := range rpm.files {
		if f == path {
			// Send a fake file
			fmt.Fprintf(w, "Some data here!")
			return
		}
	}
	if !strings.HasSuffix(path, "/") {
		path += "/"
	}
	for _, f := range rpm.files {
		if strings.HasPrefix(f, path) {
			w.WriteHeader(http.StatusOK)
			return
		}
	}
	log.Printf("%s - 404 - %s - %s", rpm, r.URL, path)
	http.NotFound(w, r)
}

func (rpm *RandomPathsModule) String() string {
	return "random_paths"
}

func (rpm *RandomPathsModule) Prefix() string {
	return ""
}

func (rpm *RandomPathsModule) RandomPrefix() bool {
	return true
}

func (rpm *RandomPathsModule) Setup() {
	for i := 0; i < 10; i++ {
		top := words.DirectoryRandomChooser()
		for j := 0; j < 10; j++ {
			bottom := words.DirectoryRandomChooser()
			for k := 0; k < 10; k++ {
				fname := words.FileRandomChooser()
				path := fmt.Sprintf("%s/%s/%s", top, bottom, fname)
				//log.Printf("Added %s", path)
				rpm.files = append(rpm.files, path)
			}
		}
	}
}

func init() {
	RegisterModule(NewRandomPathsModule())
}
