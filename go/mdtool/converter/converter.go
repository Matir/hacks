package converter

import (
	"bytes"
	_ "embed"
	"html/template"
	"io"

	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark-highlighting/v2"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/parser"
	"github.com/yuin/goldmark/renderer/html"
)

//go:embed default.css
var defaultCSS string

var pageTemplate = template.Must(template.New("page").Parse(`<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {{- if .CSS }}
    <style>
    {{ .CSS }}
    </style>
    {{- end }}
</head>
<body>
    <div class="markdown-body">
    {{ .Content }}
    </div>
    {{- if .Mermaid }}
    <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ startOnLoad: true });
    </script>
    {{- end }}
    {{- if .Watch }}
    <script>
    const evtSource = new EventSource("/events");
    evtSource.onmessage = (event) => {
        if (event.data === "reload") {
            window.location.reload();
        }
    };
    </script>
    {{- end }}
</body>
</html>`))

// Converter holds configuration options for the conversion process.
type Converter struct {
	CSS       string
	Highlight bool
	Mermaid   bool
	Watch     bool
	gm        goldmark.Markdown
}

// New returns a new Converter with the specified options.
func New(css string, highlight bool, mermaid bool) *Converter {
	if css == "" {
		css = defaultCSS
	}

	extensions := []goldmark.Extender{
		extension.GFM,
	}

	if highlight {
		extensions = append(extensions, highlighting.NewHighlighting())
	}

	gm := goldmark.New(
		goldmark.WithExtensions(extensions...),
		goldmark.WithParserOptions(
			parser.WithAutoHeadingID(),
		),
		goldmark.WithRendererOptions(
			html.WithUnsafe(),
		),
	)

	return &Converter{
		CSS:       css,
		Highlight: highlight,
		Mermaid:   mermaid,
		gm:        gm,
	}
}

// Convert renders Markdown from r to HTML in w.
func (c *Converter) Convert(r io.Reader, w io.Writer) error {
	md, err := io.ReadAll(r)
	if err != nil {
		return err
	}

	// Use a pipe or buffer if we want to be more efficient, 
	// but for template execution we need the rendered content.
	// For now, let's render to a string and use template.HTML to avoid escaping.
	var content bytes.Buffer
	if err := c.gm.Convert(md, &content); err != nil {
		return err
	}

	data := struct {
		CSS     template.CSS
		Content template.HTML
		Mermaid bool
		Watch   bool
	}{
		CSS:     template.CSS(c.CSS),
		Content: template.HTML(content.String()),
		Mermaid: c.Mermaid,
		Watch:   c.Watch,
	}

	return pageTemplate.Execute(w, data)
}
