package main

import (
	"math/rand"
	"time"

	"github.com/matir/hacks/go/demoserver/modules"
	"github.com/matir/hacks/go/demoserver/server"
)

func main() {
	rand.Seed(time.Now().UnixNano())

	srv := server.NewDemoServer("127.0.0.1:8123")
	srv.RegisterModule(modules.GetModuleByName("random_paths"))
	srv.ListenAndServe()
}
