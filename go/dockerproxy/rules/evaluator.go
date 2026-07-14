// Package rules implements policy ruleset models and matching algorithms for API requests.
package rules

import (
	"encoding/json"
	"net/url"
	"regexp"
	"strings"
)

// IdentifyCommandType classifies incoming Docker API requests into standard operation categories.
func IdentifyCommandType(method, uri string) string {
	upperMethod := strings.ToUpper(method)
	path := uri
	if idx := strings.Index(uri, "?"); idx != -1 {
		path = uri[:idx]
	}

	if upperMethod == "POST" && strings.HasSuffix(path, "/containers/create") {
		return "create"
	}
	if upperMethod == "POST" && strings.HasSuffix(path, "/exec") {
		return "exec"
	}
	if upperMethod == "POST" && strings.Contains(path, "/build") {
		return "build"
	}
	if upperMethod == "GET" && (strings.HasSuffix(path, "/containers/json") || strings.HasSuffix(path, "/images/json")) {
		return "list"
	}
	if upperMethod == "DELETE" {
		return "delete"
	}
	if upperMethod == "GET" {
		return "inspect"
	}
	return "other"
}

// Evaluate inspects the HTTP request method, URI path, command category, and deserialized payload against the ruleset.
// Returns the resulting Action, custom denial Message (if any), and the matched Rule ID (or "default").
func Evaluate(method, uri string, bodySnippet []byte, rs *Ruleset) (Action, string, string) {
	if rs == nil {
		return ActionAllow, "", "default"
	}

	upperMethod := strings.ToUpper(method)
	cmdType := IdentifyCommandType(method, uri)

	for _, rule := range rs.Rules {
		// 1. Match HTTP Method
		if len(rule.Methods) > 0 {
			methodMatched := false
			for _, m := range rule.Methods {
				if strings.ToUpper(m) == upperMethod || m == "*" {
					methodMatched = true
					break
				}
			}
			if !methodMatched {
				continue
			}
		}

		// 2. Match Command Type
		if len(rule.CommandTypes) > 0 {
			cmdMatched := false
			for _, ct := range rule.CommandTypes {
				if strings.ToLower(ct) == cmdType {
					cmdMatched = true
					break
				}
			}
			if !cmdMatched {
				continue
			}
		}

		// 3. Match URI Path Pattern
		if rule.PathPattern != "" {
			re, err := regexp.Compile(rule.PathPattern)
			if err != nil || !re.MatchString(uri) {
				continue
			}
		}

		// 4. Match Body Pattern (Text regex fallback)
		if rule.BodyPattern != "" {
			re, err := regexp.Compile(rule.BodyPattern)
			if err != nil || !re.Match(bodySnippet) {
				continue
			}
		}

		// 5. Semantic Container Create Matching
		if rule.ContainerCreate != nil {
			if cmdType != "create" {
				continue
			}
			var req ContainerCreateRequest
			if len(bodySnippet) > 0 {
				_ = json.Unmarshal(bodySnippet, &req)
			}

			if !evaluateContainerCreate(rule.ContainerCreate, &req, uri, rule.Action) {
				continue
			}
		}

		// 6. Semantic Exec Create Matching
		if rule.ExecCreate != nil {
			if cmdType != "exec" {
				continue
			}
			var req ExecCreateRequest
			if len(bodySnippet) > 0 {
				_ = json.Unmarshal(bodySnippet, &req)
			}

			if !evaluateExecCreate(rule.ExecCreate, &req, uri, rule.Action) {
				continue
			}
		}

		// All specified conditions matched
		msg := rule.Message
		if msg == "" && rule.Action == ActionDeny {
			msg = "Request denied by policy rule: " + rule.ID
		}
		ruleID := rule.ID
		if ruleID == "" {
			ruleID = "anonymous-rule"
		}
		return rule.Action, msg, ruleID
	}

	defaultAction := rs.DefaultAction
	if defaultAction == "" {
		defaultAction = ActionAllow
	}
	return defaultAction, "", "default"
}

func evaluateContainerCreate(cc *ContainerCreateRule, req *ContainerCreateRequest, uri string, action Action) bool {
	if cc.Privileged != nil {
		isPriv := false
		if req.HostConfig != nil {
			isPriv = req.HostConfig.Privileged
		}
		if isPriv != *cc.Privileged {
			return false
		}
	}

	if action == ActionDeny {
		// For ActionDeny, rule triggers if ANY allowlist condition is violated
		if len(cc.AllowedMounts) > 0 {
			violation := false
			if req.HostConfig != nil {
				for _, b := range req.HostConfig.Binds {
					if !matchesAnyRegex(b, cc.AllowedMounts) {
						violation = true
						break
					}
				}
				for _, m := range req.HostConfig.Mounts {
					targetStr := m.Source + ":" + m.Target
					if !matchesAnyRegex(targetStr, cc.AllowedMounts) && !matchesAnyRegex(m.Target, cc.AllowedMounts) {
						violation = true
						break
					}
				}
			}
			if violation {
				return true
			}
		}

		if len(cc.AllowedPorts) > 0 {
			violation := false
			if req.HostConfig != nil && len(req.HostConfig.PortBindings) > 0 {
				for p := range req.HostConfig.PortBindings {
					if !containsString(cc.AllowedPorts, p.String()) {
						violation = true
						break
					}
				}
			}
			if violation {
				return true
			}
		}

		if len(cc.AllowedImages) > 0 {
			img := ""
			if req.Config != nil {
				img = req.Config.Image
			}
			if !matchesAnyRegex(img, cc.AllowedImages) {
				return true
			}
		}

		if len(cc.AllowedNames) > 0 {
			u, _ := url.Parse(uri)
			name := ""
			if u != nil {
				name = u.Query().Get("name")
			}
			if !matchesAnyRegex(name, cc.AllowedNames) {
				return true
			}
		}

		// If cc had allowlists but none were violated, and Privileged didn't trigger alone
		if len(cc.AllowedMounts) > 0 || len(cc.AllowedPorts) > 0 || len(cc.AllowedImages) > 0 || len(cc.AllowedNames) > 0 {
			if cc.Privileged == nil {
				return false
			}
		}
		return true
	}

	// For ActionAllow, all specified allowlists must be satisfied
	if len(cc.AllowedMounts) > 0 {
		if req.HostConfig != nil {
			for _, b := range req.HostConfig.Binds {
				if !matchesAnyRegex(b, cc.AllowedMounts) {
					return false
				}
			}
		}
	}
	if len(cc.AllowedPorts) > 0 {
		if req.HostConfig != nil {
			for p := range req.HostConfig.PortBindings {
				if !containsString(cc.AllowedPorts, p.String()) {
					return false
				}
			}
		}
	}
	if len(cc.AllowedImages) > 0 {
		img := ""
		if req.Config != nil {
			img = req.Config.Image
		}
		if !matchesAnyRegex(img, cc.AllowedImages) {
			return false
		}
	}
	if len(cc.AllowedNames) > 0 {
		u, _ := url.Parse(uri)
		name := ""
		if u != nil {
			name = u.Query().Get("name")
		}
		if !matchesAnyRegex(name, cc.AllowedNames) {
			return false
		}
	}

	return true
}

func evaluateExecCreate(ec *ExecCreateRule, req *ExecCreateRequest, uri string, action Action) bool {
	if action == ActionDeny {
		if len(ec.AllowedCommands) > 0 {
			cmdStr := strings.Join(req.Cmd, " ")
			if !matchesAnyRegex(cmdStr, ec.AllowedCommands) {
				return true
			}
		}
		if len(ec.AllowedContainers) > 0 {
			path := uri
			if idx := strings.Index(uri, "?"); idx != -1 {
				path = uri[:idx]
			}
			parts := strings.Split(strings.Trim(path, "/"), "/")
			containerName := ""
			for i := 0; i < len(parts)-1; i++ {
				if parts[i] == "containers" {
					containerName = parts[i+1]
					break
				}
			}
			if !matchesAnyRegex(containerName, ec.AllowedContainers) {
				return true
			}
		}
		return false
	}

	if len(ec.AllowedCommands) > 0 {
		cmdStr := strings.Join(req.Cmd, " ")
		if !matchesAnyRegex(cmdStr, ec.AllowedCommands) {
			return false
		}
	}
	if len(ec.AllowedContainers) > 0 {
		path := uri
		if idx := strings.Index(uri, "?"); idx != -1 {
			path = uri[:idx]
		}
		parts := strings.Split(strings.Trim(path, "/"), "/")
		containerName := ""
		for i := 0; i < len(parts)-1; i++ {
			if parts[i] == "containers" {
				containerName = parts[i+1]
				break
			}
		}
		if !matchesAnyRegex(containerName, ec.AllowedContainers) {
			return false
		}
	}
	return true
}

func matchesAnyRegex(s string, patterns []string) bool {
	for _, p := range patterns {
		re, err := regexp.Compile(p)
		if err == nil && re.MatchString(s) {
			return true
		}
	}
	return false
}

func containsString(list []string, item string) bool {
	for _, s := range list {
		if s == item {
			return true
		}
	}
	return false
}
