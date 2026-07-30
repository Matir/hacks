package prompt

import (
	"bytes"
	_ "embed"
	"fmt"
	"os"
	"text/template"
)

//go:embed prompt.md
var bundledDefaultPrompt string

// TemplateContext holds values injected into the prompt template execution.
type TemplateContext struct {
	Input        string
	SystemPrompt string
	Variables    map[string]string
}

// Loader manages prompt template loading and rendering.
type Loader struct {
	customFilePath string
}

// NewLoader creates a prompt Loader with the target custom file path.
func NewLoader(customFilePath string) *Loader {
	return &Loader{
		customFilePath: customFilePath,
	}
}

// LoadTemplate resolves the prompt template content and origin source.
// Resolution order:
// 1. Inline request template string (if non-empty) -> source: "inline_override"
// 2. Custom file at customFilePath (if file exists) -> source: "custom_file"
// 3. Embedded bundled template fallback -> source: "bundled"
func (l *Loader) LoadTemplate(inline string) (*template.Template, string, error) {
	if inline != "" {
		tmpl, err := template.New("inline_prompt").Parse(inline)
		if err != nil {
			return nil, "", fmt.Errorf("failed to parse inline template: %w", err)
		}
		return tmpl, "inline_override", nil
	}

	if l.customFilePath != "" {
		data, err := os.ReadFile(l.customFilePath)
		if err == nil && len(data) > 0 {
			tmpl, err := template.New("custom_prompt").Parse(string(data))
			if err != nil {
				return nil, "", fmt.Errorf("failed to parse custom prompt file %s: %w", l.customFilePath, err)
			}
			return tmpl, "custom_file", nil
		}
	}

	tmpl, err := template.New("bundled_prompt").Parse(bundledDefaultPrompt)
	if err != nil {
		return nil, "", fmt.Errorf("failed to parse bundled default prompt: %w", err)
	}
	return tmpl, "bundled", nil
}

// Execute renders the compiled template with the provided context data.
func (l *Loader) Execute(tmpl *template.Template, ctx TemplateContext) (string, error) {
	if ctx.Variables == nil {
		ctx.Variables = make(map[string]string)
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, ctx); err != nil {
		return "", fmt.Errorf("template execution error: %w", err)
	}
	return buf.String(), nil
}
