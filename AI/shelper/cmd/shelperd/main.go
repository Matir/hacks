package main

import (
	"context"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"shelper/config"
	"shelper/daemon"
	"shelper/llm"
	slog "shelper/log"
	"shelper/prompt"
)

func main() {
	// 1. Load Configuration (pass CLI args)
	cfg, err := config.LoadConfig(os.Args[1:])
	if err != nil {
		log.Fatalf("[FATAL] Configuration load failed: %v", err)
	}

	// 2. Initialize Logger
	var logOut io.Writer = io.Discard
	if cfg.LogFile != "" {
		f, err := os.OpenFile(cfg.LogFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err != nil {
			log.Fatalf("[FATAL] Failed to open log file %s: %v", cfg.LogFile, err)
		}
		defer f.Close()
		logOut = f
	}

	logger := slog.NewLogger(logOut, cfg.LogLevel)
	logger.Info("SHelper daemon starting...")
	logger.Info("Resolved socket path: %s", cfg.SocketPath)

	// Mask API keys
	logger.Mask(cfg.GeminiAPIKey)
	logger.Mask(cfg.OpenAIAPIKey)

	// 3. Initialize Prompt Loader
	promptLoader := prompt.NewLoader(cfg.CustomPromptPath)

	// 4. Initialize LLM Providers
	registry := llm.NewRegistry()
	var registeredCount int

	// Proactively attempt initialization of Google Gen AI Provider
	if googleProv, err := llm.NewGoogleGenAIProvider(cfg.GeminiAPIKey); err == nil {
		registry.Register(googleProv)
		logger.Info("Google Gen AI Provider initialized successfully")
		registeredCount++
	} else {
		logger.Warning("Google Gen AI Provider init deferred: %v", err)
	}

	// Proactively attempt initialization of OpenAI Provider
	if openaiProv, err := llm.NewOpenAIProvider(cfg.OpenAIAPIKey); err == nil {
		registry.Register(openaiProv)
		logger.Info("OpenAI Provider initialized successfully")
		registeredCount++
	} else {
		logger.Warning("OpenAI Provider init deferred: %v", err)
	}

	// CRITICAL check: Exit immediately if no providers are registered due to missing credentials
	if registeredCount == 0 {
		os.Stderr.Write([]byte("Error: No LLM provider credentials configured. Daemon cannot start.\n"))
		os.Exit(1)
	}

	// 5. Define Request Handler Hook with resilient structured errors
	requestHandler := func(ctx context.Context, req *daemon.SocketRequest) (*daemon.SocketResponse, error) {
		startTime := time.Now()
		logger.Info("Processing request ID: %s", req.ID)

		// A. Validate Request Input
		if req.Input == "" {
			logger.Warning("Validation failed: empty input string for request %s", req.ID)
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "INVALID_REQUEST",
					Message: "field 'input' cannot be empty",
				},
			}, nil
		}

		// B. Resolve LLM Provider
		providerName := req.Provider
		if providerName == "" {
			providerName = cfg.DefaultProvider
		}
		// Convert gemini alias to google if needed
		if providerName == "gemini" {
			providerName = "google"
		}

		provider, err := registry.Get(providerName)
		if err != nil {
			logger.Warning("Failed to resolve provider %s: %v", providerName, err)
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "INVALID_REQUEST",
					Message: "unsupported or unregistered provider",
					Details: err.Error(),
				},
			}, nil
		}

		// C. Load and Render Prompt Template
		tmpl, templateSource, err := promptLoader.LoadTemplate(req.Template)
		if err != nil {
			logger.Error("Failed to load prompt template for request %s: %v", req.ID, err)
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "TEMPLATE_ERROR",
					Message: "failed to load template",
					Details: err.Error(),
				},
			}, nil
		}

		formattedPrompt, err := promptLoader.Execute(tmpl, prompt.TemplateContext{
			Input:     req.Input,
			Variables: req.Variables,
		})
		if err != nil {
			logger.Error("Failed to execute/render template for request %s: %v", req.ID, err)
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "TEMPLATE_ERROR",
					Message: "failed to execute/render template",
					Details: err.Error(),
				},
			}, nil
		}

		// D. Dispatch LLM API Call
		// Override model default if not explicitly specified in request
		modelName := req.Model
		if modelName == "" {
			modelName = cfg.DefaultModel
		}

		genReq := &llm.GenerateRequest{
			Model:       modelName,
			UserPrompt:  formattedPrompt,
			Temperature: req.Temperature,
		}

		resp, err := provider.Generate(ctx, genReq)
		if err != nil {
			logger.Error("API Generation failed for request %s on provider %s: %v", req.ID, providerName, err)
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "PROVIDER_ERROR",
					Message: "upstream LLM generation failed",
					Details: err.Error(),
				},
			}, nil
		}

		latencyMs := time.Since(startTime).Milliseconds()

		// Log success telemetry
		logger.LogLLMRequest(req.ID, resp.Provider, resp.Model, req.Input, resp.Output, latencyMs)

		// E. Construct and Return Success Payload
		return &daemon.SocketResponse{
			ID:     req.ID,
			Status: "success",
			Output: resp.Output,
			Metadata: daemon.ResponseMetadata{
				Provider:       resp.Provider,
				Model:          resp.Model,
				LatencyMs:      latencyMs,
				TemplateSource: templateSource,
			},
		}, nil
	}

	// 6. Initialize & Start Daemon (pass custom logger)
	d := daemon.NewDaemon(cfg.SocketPath, requestHandler, logger)
	if err := d.Start(); err != nil {
		logger.Error("[FATAL] Daemon failed to start: %v", err)
		os.Exit(1)
	}

	// 7. Handle Graceful Shutdown Signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	sig := <-sigChan
	logger.Info("Received signal %v. Initiating graceful shutdown...", sig)
	d.Stop()
}
