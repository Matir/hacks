package log

import (
	"fmt"
	"io"
	"strings"
	"time"
)

type Level int

const (
	LevelInfo Level = iota
	LevelWarning
	LevelError
)

type Logger struct {
	out        io.Writer
	level      Level
	maskedKeys []string
}

// NewLogger parses log level and initializes a Logger.
func NewLogger(out io.Writer, levelStr string) *Logger {
	level := LevelInfo
	switch strings.ToLower(strings.TrimSpace(levelStr)) {
	case "warning", "warn":
		level = LevelWarning
	case "error":
		level = LevelError
	}
	return &Logger{
		out:        out,
		level:      level,
		maskedKeys: make([]string, 0),
	}
}

// Mask registers a sensitive value to be replaced with [API_KEY_MASKED].
func (l *Logger) Mask(key string) {
	if key == "" {
		return
	}
	l.maskedKeys = append(l.maskedKeys, key)
}

// applyMask replaces all registered sensitive values.
func (l *Logger) applyMask(msg string) string {
	for _, key := range l.maskedKeys {
		msg = strings.ReplaceAll(msg, key, "[API_KEY_MASKED]")
	}
	return msg
}

// formatLog prefix with time, level, and applies masking.
func (l *Logger) formatLog(levelStr, format string, v ...interface{}) string {
	msg := fmt.Sprintf(format, v...)
	masked := l.applyMask(msg)
	timestamp := time.Now().Format("2006/01/02 15:04:05")
	return fmt.Sprintf("%s [%s] %s\n", timestamp, levelStr, masked)
}

// Info logs messages at INFO level.
func (l *Logger) Info(format string, v ...interface{}) {
	if l.level <= LevelInfo {
		l.out.Write([]byte(l.formatLog("INFO", format, v...)))
	}
}

// Warning logs messages at WARNING level.
func (l *Logger) Warning(format string, v ...interface{}) {
	if l.level <= LevelWarning {
		l.out.Write([]byte(l.formatLog("WARNING", format, v...)))
	}
}

// Error logs messages at ERROR level.
func (l *Logger) Error(format string, v ...interface{}) {
	if l.level <= LevelError {
		l.out.Write([]byte(l.formatLog("ERROR", format, v...)))
	}
}

// LogLLMRequest prints detailed LLM call metrics and inputs (with masking).
func (l *Logger) LogLLMRequest(id, provider, model, prompt, response string, latencyMs int64) {
	if l.level <= LevelInfo {
		l.Info("LLM Request ID: %s | Provider: %s | Model: %s\nPrompt: %s\nResponse: %s\nLatency: %dms",
			id, provider, model, prompt, response, latencyMs)
	}
}
