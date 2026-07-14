package rules

import (
	"testing"
)

func TestIdentifyCommandType(t *testing.T) {
	tests := []struct {
		method string
		uri    string
		want   string
	}{
		{"POST", "/v1.43/containers/create?name=foo", "create"},
		{"POST", "/v1.43/containers/123abc_/exec", "exec"},
		{"POST", "/v1.43/build?t=myimg", "build"},
		{"GET", "/v1.43/containers/json?all=1", "list"},
		{"GET", "/v1.43/images/json", "list"},
		{"DELETE", "/v1.43/containers/myc?force=1", "delete"},
		{"GET", "/v1.43/version", "inspect"},
	}

	for _, tt := range tests {
		got := IdentifyCommandType(tt.method, tt.uri)
		if got != tt.want {
			t.Errorf("IdentifyCommandType(%q, %q) = %q, want %q", tt.method, tt.uri, got, tt.want)
		}
	}
}

func TestEvaluate_SemanticCommandType(t *testing.T) {
	rs := &Ruleset{
		DefaultAction: ActionAllow,
		Rules: []SemanticRule{
			{
				ID:           "deny-build",
				Action:       ActionDeny,
				CommandTypes: []string{"build"},
				Message:      "Builds prohibited",
			},
		},
	}

	action, msg, ruleID := Evaluate("POST", "/v1.43/build?t=foo", nil, rs)
	if action != ActionDeny || ruleID != "deny-build" || msg != "Builds prohibited" {
		t.Errorf("expected deny-build, got (%s, %s, %q)", action, ruleID, msg)
	}

	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create", nil, rs)
	if action != ActionAllow || ruleID != "default" {
		t.Errorf("expected allow default on create, got (%s, %s)", action, ruleID)
	}
}

func TestEvaluate_SemanticContainerCreate_PrivilegedAndMounts(t *testing.T) {
	privTrue := true
	rs := &Ruleset{
		DefaultAction: ActionAllow,
		Rules: []SemanticRule{
			{
				ID:     "deny-priv",
				Action: ActionDeny,
				ContainerCreate: &ContainerCreateRule{
					Privileged: &privTrue,
				},
			},
			{
				ID:     "deny-unauthorized-mounts",
				Action: ActionDeny,
				ContainerCreate: &ContainerCreateRule{
					AllowedMounts: []string{"^/var/log/.*", "^/tmp/.*"},
				},
			},
		},
	}

	// 1. Privileged container create -> Deny
	bodyPriv := []byte(`{"Image":"ubuntu","HostConfig":{"Privileged":true}}`)
	action, _, ruleID := Evaluate("POST", "/v1.43/containers/create", bodyPriv, rs)
	if action != ActionDeny || ruleID != "deny-priv" {
		t.Errorf("expected deny-priv, got (%s, %s)", action, ruleID)
	}

	// 2. Unprivileged container create with allowed mounts -> Allow
	bodyAllowedMount := []byte(`{"Image":"ubuntu","HostConfig":{"Privileged":false,"Binds":["/var/log/app:/app/log"]}}`)
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create", bodyAllowedMount, rs)
	if action != ActionAllow || ruleID != "default" {
		t.Errorf("expected allow default, got (%s, %s)", action, ruleID)
	}

	// 3. Unprivileged container create with forbidden mount -> Deny
	bodyBadMount := []byte(`{"Image":"ubuntu","HostConfig":{"Binds":["/etc:/host_etc:ro"]}}`)
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create", bodyBadMount, rs)
	if action != ActionDeny || ruleID != "deny-unauthorized-mounts" {
		t.Errorf("expected deny-unauthorized-mounts, got (%s, %s)", action, ruleID)
	}
}

func TestEvaluate_SemanticContainerCreate_PortsImagesAndNames(t *testing.T) {
	rs := &Ruleset{
		DefaultAction: ActionAllow,
		Rules: []SemanticRule{
			{
				ID:     "restrict-ports",
				Action: ActionDeny,
				ContainerCreate: &ContainerCreateRule{
					AllowedPorts: []string{"80/tcp", "443/tcp"},
				},
			},
			{
				ID:     "restrict-images",
				Action: ActionDeny,
				ContainerCreate: &ContainerCreateRule{
					AllowedImages: []string{"^myrepo/.*"},
				},
			},
			{
				ID:     "restrict-names",
				Action: ActionDeny,
				ContainerCreate: &ContainerCreateRule{
					AllowedNames: []string{"^app-.*"},
				},
			},
		},
	}

	// 1. Allowed port -> Allow
	bodyPortOK := []byte(`{"Image":"myrepo/web","HostConfig":{"PortBindings":{"80/tcp":[{"HostPort":"8080"}]}}}`)
	action, _, ruleID := Evaluate("POST", "/v1.43/containers/create?name=app-web", bodyPortOK, rs)
	if action != ActionAllow {
		t.Errorf("expected allow on valid port/image/name, got (%s, %s)", action, ruleID)
	}

	// 2. Forbidden port (22/tcp) -> Deny
	bodyPortBad := []byte(`{"Image":"myrepo/web","HostConfig":{"PortBindings":{"22/tcp":[{"HostPort":"2222"}]}}}`)
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create?name=app-ssh", bodyPortBad, rs)
	if action != ActionDeny || ruleID != "restrict-ports" {
		t.Errorf("expected deny restrict-ports, got (%s, %s)", action, ruleID)
	}

	// 3. Forbidden image -> Deny
	bodyImgBad := []byte(`{"Image":"untrusted/cryptominer"}`)
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create?name=app-test", bodyImgBad, rs)
	if action != ActionDeny || ruleID != "restrict-images" {
		t.Errorf("expected deny restrict-images, got (%s, %s)", action, ruleID)
	}

	// 4. Forbidden container name -> Deny
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/create?name=root_container", []byte(`{"Image":"myrepo/web"}`), rs)
	if action != ActionDeny || ruleID != "restrict-names" {
		t.Errorf("expected deny restrict-names, got (%s, %s)", action, ruleID)
	}
}

func TestEvaluate_SemanticExecCreate(t *testing.T) {
	rs := &Ruleset{
		DefaultAction: ActionAllow,
		Rules: []SemanticRule{
			{
				ID:     "restrict-exec",
				Action: ActionDeny,
				ExecCreate: &ExecCreateRule{
					AllowedCommands:   []string{"^ls.*", "^cat /var/log/.*"},
					AllowedContainers: []string{"^app-.*"},
				},
			},
		},
	}

	// 1. Allowed exec command on allowed container -> Allow
	bodyOK := []byte(`{"Cmd":["cat /var/log/syslog"]}`)
	action, _, ruleID := Evaluate("POST", "/v1.43/containers/app-web-1/exec", bodyOK, rs)
	if action != ActionAllow {
		t.Errorf("expected allow on valid exec, got (%s, %s)", action, ruleID)
	}

	// 2. Forbidden command (`sh`) -> Deny
	bodyBadCmd := []byte(`{"Cmd":["/bin/sh"]}`)
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/app-web-1/exec", bodyBadCmd, rs)
	if action != ActionDeny || ruleID != "restrict-exec" {
		t.Errorf("expected deny restrict-exec on forbidden cmd, got (%s, %s)", action, ruleID)
	}

	// 3. Forbidden container target -> Deny
	action, _, ruleID = Evaluate("POST", "/v1.43/containers/db-container/exec", bodyOK, rs)
	if action != ActionDeny || ruleID != "restrict-exec" {
		t.Errorf("expected deny restrict-exec on forbidden container target, got (%s, %s)", action, ruleID)
	}
}

func TestEvaluate_MatchesPathAndMethod(t *testing.T) {
	rs := &Ruleset{
		DefaultAction: ActionAllow,
		Rules: []PolicyRule{
			{
				ID:          "block-create",
				Methods:     []string{"POST"},
				PathPattern: "^/v[\\d\\.]+/containers/create.*",
				Action:      ActionDeny,
				Message:     "Container creation blocked",
			},
		},
	}

	action, msg, ruleID := Evaluate("POST", "/v1.43/containers/create?name=foo", nil, rs)
	if action != ActionDeny {
		t.Errorf("expected action deny, got %s", action)
	}
	if msg != "Container creation blocked" {
		t.Errorf("expected custom message, got %q", msg)
	}
	if ruleID != "block-create" {
		t.Errorf("expected ruleID block-create, got %s", ruleID)
	}
}
