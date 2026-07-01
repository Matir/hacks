// Package main is the entrypoint for the Docker API proxy CLI utility.
package main

import (
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/Matir/hacks/go/dockerproxy/config"
	"github.com/Matir/hacks/go/dockerproxy/listener"
	"github.com/Matir/hacks/go/dockerproxy/proxy"
	"github.com/Matir/hacks/go/dockerproxy/recorder"
)

func main() {
	listenAddr := flag.String("listen", "unix:///tmp/dockerproxy.sock", "Address to listen on (unix://path or tcp://host:port)")
	upstreamAddr := flag.String("upstream", "unix:///var/run/docker.sock", "Upstream Docker daemon address")
	rulesPath := flag.String("rules", "", "Path to policy ruleset YAML file")
	recordPath := flag.String("record", "", "Path to traffic recording JSON Lines audit file (- for stdout)")
	flag.Parse()

	log.Printf("Starting Docker API Proxy...")
	log.Printf("Listen Address: %s", *listenAddr)
	log.Printf("Upstream Address: %s", *upstreamAddr)

	ln, err := listener.New(*listenAddr)
	if err != nil {
		log.Fatalf("Failed to create listener on %s: %v", *listenAddr, err)
	}
	defer func() { _ = ln.Close() }()

	p, err := proxy.New(*upstreamAddr)
	if err != nil {
		log.Fatalf("Failed to initialize proxy targeting %s: %v", *upstreamAddr, err)
	}

	if *recordPath != "" {
		recWriter, err := recorder.NewWriter(*recordPath)
		if err != nil {
			log.Fatalf("Failed initializing traffic recorder at %q: %v", *recordPath, err)
		}
		defer func() { _ = recWriter.Close() }()
		log.Printf("Traffic recording enabled targeting sink: %s", *recordPath)
		p.Use(recorder.Middleware(recWriter))
	}

	if *rulesPath != "" {
		rs, err := config.LoadRuleset(*rulesPath)
		if err != nil {
			log.Fatalf("Failed loading ruleset %q: %v", *rulesPath, err)
		}
		log.Printf("Loaded policy ruleset from %s (%d rules)", *rulesPath, len(rs.Rules))
		p.Use(proxy.RuleEvaluator(rs))
	}

	srv := &http.Server{
		Handler: p,
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		if err := srv.Serve(ln); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	<-sigChan
	log.Println("Shutting down Docker API Proxy...")
	_ = srv.Close()
}
