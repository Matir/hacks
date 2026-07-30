package prompt

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoader_FormatPrompt(t *testing.T) {
	tmpDir := t.TempDir()
	customFile := filepath.Join(tmpDir, "prompt.md")

	t.Run("Default embedded template", func(t *testing.T) {
		loader := NewLoader("/non/existent/path/prompt.md")
		tmpl, source, err := loader.LoadTemplate("")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if source != "bundled" {
			t.Errorf("got source %q, want 'bundled'", source)
		}

		ctx := TemplateContext{
			Input: "list files",
			Variables: map[string]string{
				"shell": "zsh",
			},
		}
		output, err := loader.Execute(tmpl, ctx)
		if err != nil {
			t.Fatalf("execute error: %v", err)
		}
		if output == "" {
			t.Errorf("expected non-empty formatted prompt")
		}
	})

	t.Run("Custom file override", func(t *testing.T) {
		content := "Custom System. Shell: {{.Variables.shell}}. Input: {{.Input}}"
		if err := os.WriteFile(customFile, []byte(content), 0644); err != nil {
			t.Fatalf("failed writing custom prompt: %v", err)
		}

		loader := NewLoader(customFile)
		tmpl, source, err := loader.LoadTemplate("")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if source != "custom_file" {
			t.Errorf("got source %q, want 'custom_file'", source)
		}

		ctx := TemplateContext{
			Input: "disk space",
			Variables: map[string]string{
				"shell": "bash",
			},
		}
		output, err := loader.Execute(tmpl, ctx)
		if err != nil {
			t.Fatalf("execute error: %v", err)
		}
		want := "Custom System. Shell: bash. Input: disk space"
		if output != want {
			t.Errorf("got %q, want %q", output, want)
		}
	})

	t.Run("Inline request template override", func(t *testing.T) {
		loader := NewLoader("/non/existent/path/prompt.md")
		inline := "Inline template: {{.Input}}"
		tmpl, source, err := loader.LoadTemplate(inline)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if source != "inline_override" {
			t.Errorf("got source %q, want 'inline_override'", source)
		}

		output, err := loader.Execute(tmpl, TemplateContext{Input: "hello"})
		if err != nil {
			t.Fatalf("execute error: %v", err)
		}
		want := "Inline template: hello"
		if output != want {
			t.Errorf("got %q, want %q", output, want)
		}
	})
}
