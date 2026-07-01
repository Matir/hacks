// Package config provides configuration parsing, error types, and shared utilities.
package config

import (
	"errors"
	"fmt"
)

var (
	// ErrInvalidRule indicates that a policy rule definition is invalid or malformed.
	ErrInvalidRule = errors.New("invalid policy rule")
	// ErrRulesetNotFound indicates that the specified ruleset file could not be read.
	ErrRulesetNotFound = errors.New("ruleset file not found")
	// ErrUnsupportedSocket indicates that a socket scheme other than unix:// or tcp:// was specified.
	ErrUnsupportedSocket = errors.New("unsupported socket address scheme (must be unix:// or tcp://)")
	// ErrListenerClosed indicates operations attempted on a closed listener.
	ErrListenerClosed = errors.New("listener closed")
)

// RuleError wraps an error occurring within a specific policy rule evaluation or parse step.
type RuleError struct {
	RuleID  string
	Message string
	Err     error
}

func (e *RuleError) Error() string {
	if e.RuleID != "" {
		return fmt.Sprintf("rule %q: %s: %v", e.RuleID, e.Message, e.Err)
	}
	return fmt.Sprintf("%s: %v", e.Message, e.Err)
}

func (e *RuleError) Unwrap() error {
	return e.Err
}
