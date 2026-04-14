package converter

import (
	"bytes"
	"strings"
	"testing"
)

func TestConvertBasic(t *testing.T) {
	c := New("", false, false)
	input := "# Hello World"
	var buf bytes.Buffer
	if err := c.Convert(strings.NewReader(input), &buf); err != nil {
		t.Fatalf("Convert failed: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "<h1 id=\"hello-world\">Hello World</h1>") {
		t.Errorf("Expected <h1 id=\"hello-world\">Hello World</h1> in output, got %s", output)
	}
	if !strings.Contains(output, "<style>") {
		t.Errorf("Expected <style> tag in output for default CSS")
	}
}

func TestConvertGFM(t *testing.T) {
	c := New("", false, false)
	input := "| header |\n| --- |\n| cell |"
	var buf bytes.Buffer
	if err := c.Convert(strings.NewReader(input), &buf); err != nil {
		t.Fatalf("Convert failed: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "<table>") {
		t.Errorf("Expected <table> in output for GFM, got %s", output)
	}
}

func TestConvertHighlight(t *testing.T) {
	c := New("", true, false)
	input := "```go\nfunc main() {}\n```"
	var buf bytes.Buffer
	if err := c.Convert(strings.NewReader(input), &buf); err != nil {
		t.Fatalf("Convert failed: %v", err)
	}

	output := buf.String()
	// Chroma usually adds inline styles or specific classes
	if !strings.Contains(output, "color:") && !strings.Contains(output, "style=") {
		t.Errorf("Expected syntax highlighting in output, got %s", output)
	}
}

func TestConvertMermaid(t *testing.T) {
	c := New("", false, true)
	input := "graph TD; A-->B;"
	var buf bytes.Buffer
	if err := c.Convert(strings.NewReader(input), &buf); err != nil {
		t.Fatalf("Convert failed: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, "mermaid.initialize") {
		t.Errorf("Expected mermaid script in output, got %s", output)
	}
}

func TestConvertCustomCSS(t *testing.T) {
	customCSS := "body { color: red; }"
	c := New(customCSS, false, false)
	input := "# Red Header"
	var buf bytes.Buffer
	if err := c.Convert(strings.NewReader(input), &buf); err != nil {
		t.Fatalf("Convert failed: %v", err)
	}

	output := buf.String()
	if !strings.Contains(output, customCSS) {
		t.Errorf("Expected custom CSS in output, got %s", output)
	}
}
