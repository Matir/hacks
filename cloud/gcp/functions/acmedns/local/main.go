package main

import (
	"context"
	"log"
	"os"

	"github.com/GoogleCloudPlatform/functions-framework-go/funcframework"

	"systemoverlord.com/acmedns"
)

func main() {
	ctx := context.Background()
	os.Setenv("FUNCTION_TARGET", "AcmeDNS")
	if err := funcframework.RegisterHTTPFunctionContext(ctx, "/", acmedns.AcmeDNS); err != nil {
		log.Fatalf("funcframework.RegisterHTTPFunctionContext: %v\n", err)
	}
	// Use PORT environment variable, or default to 8080.
	port := "9123"
	if envPort := os.Getenv("PORT"); envPort != "" {
		port = envPort
	}
	log.Printf("Starting funcframework on port %v", port)
	if err := funcframework.Start(port); err != nil {
		log.Fatalf("funcframework.Start: %v\n", err)
	}
}
