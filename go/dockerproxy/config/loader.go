// Package config provides declarative configuration loading and validation.
package config

import (
	"errors"
	"os"
	"regexp"
	"strings"

	"github.com/Matir/hacks/go/dockerproxy/rules"
	"gopkg.in/yaml.v3"
)

// LoadRuleset reads and parses a YAML ruleset file from disk.
func LoadRuleset(filePath string) (*rules.Ruleset, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, ErrRulesetNotFound
		}
		return nil, err
	}

	var rs rules.Ruleset
	if err := yaml.Unmarshal(data, &rs); err != nil {
		return nil, errors.Join(ErrInvalidRule, err)
	}

	if rs.DefaultAction == "" {
		rs.DefaultAction = rules.ActionAllow
	}
	if rs.DefaultAction != rules.ActionAllow && rs.DefaultAction != rules.ActionDeny {
		return nil, &RuleError{Message: "invalid default_action (must be allow or deny)"}
	}

	// Validate rule regex patterns and actions
	for i := range rs.Rules {
		r := &rs.Rules[i]
		for j, m := range r.Methods {
			r.Methods[j] = strings.ToUpper(m)
		}
		for j, ct := range r.CommandTypes {
			r.CommandTypes[j] = strings.ToLower(ct)
		}
		if r.PathPattern != "" {
			if _, err := regexp.Compile(r.PathPattern); err != nil {
				return nil, errors.Join(ErrInvalidRule, &RuleError{RuleID: r.ID, Message: "invalid path_pattern regex", Err: err})
			}
		}
		if r.BodyPattern != "" {
			if _, err := regexp.Compile(r.BodyPattern); err != nil {
				return nil, errors.Join(ErrInvalidRule, &RuleError{RuleID: r.ID, Message: "invalid body_pattern regex", Err: err})
			}
		}
		if r.Action != rules.ActionAllow && r.Action != rules.ActionDeny && r.Action != rules.ActionFilter {
			return nil, errors.Join(ErrInvalidRule, &RuleError{RuleID: r.ID, Message: "invalid rule action (must be allow, deny, or filter)"})
		}

		if cc := r.ContainerCreate; cc != nil {
			if err := validateRegexSlice(r.ID, cc.AllowedMounts); err != nil {
				return nil, err
			}
			if err := validateRegexSlice(r.ID, cc.AllowedImages); err != nil {
				return nil, err
			}
			if err := validateRegexSlice(r.ID, cc.AllowedNames); err != nil {
				return nil, err
			}
		}

		if ec := r.ExecCreate; ec != nil {
			if err := validateRegexSlice(r.ID, ec.AllowedCommands); err != nil {
				return nil, err
			}
			if err := validateRegexSlice(r.ID, ec.AllowedContainers); err != nil {
				return nil, err
			}
		}

		if rf := r.ResponseFilter; rf != nil {
			if err := validateRegexSlice(r.ID, rf.AllowedNames); err != nil {
				return nil, err
			}
		}
	}

	return &rs, nil
}

func validateRegexSlice(ruleID string, patterns []string) error {
	for _, p := range patterns {
		if _, err := regexp.Compile(p); err != nil {
			return errors.Join(ErrInvalidRule, &RuleError{RuleID: ruleID, Message: "invalid regex pattern: " + p, Err: err})
		}
	}
	return nil
}
