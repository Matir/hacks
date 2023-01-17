package main

import (
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
)

var (
	templateMap = make(map[string]*template.Template)
)

func main() {
	staticDir := path.Join(getTemplateDir(), "static")
	fs := http.FileServer(http.Dir(staticDir))
	http.Handle("/static/", http.StripPrefix("/static/", fs))
	http.HandleFunc("/", home)
	endpoint := ":3000"
	log.Printf("Listening on %s", endpoint)
	log.Fatal(http.ListenAndServe(endpoint, nil))
}

func home(w http.ResponseWriter, r *http.Request) {
	sendTemplate(w, "index", nil)
}

func sendTemplate(w io.Writer, name string, data interface{}) error {
	tmpl, ok := templateMap[name]
	if !ok {
		return fmt.Errorf("No template named %s", name)
	}
	return tmpl.Execute(w, data)
}

func init() {
	tmplDir := getTemplateDir()
	baseTemplates := []string{path.Join(tmplDir, "base.html")}
	matches, _ := filepath.Glob(path.Join(tmplDir, "*.html"))
	for _, f := range matches {
		b := filepath.Base(f)
		e := filepath.Ext(b)
		b = strings.TrimSuffix(b, e)
		r := append(baseTemplates, f)
		templateMap[b] = template.Must(template.ParseFiles(r...))
	}
}

func getTemplateDir() string {
	tmplName := "basic"
	if newName := os.Getenv("TEMPLATE"); newName != "" {
		tmplName = newName
	}
	return path.Join("templates", tmplName)
}
