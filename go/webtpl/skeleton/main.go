package main

import (
	html "html/template"
	"log"
	"net/http"
	"os"
	"path"
)

var (
	useTemplateCache = true
	templateCache    map[string]*html.Template
	templateDir      = "./templates"
	staticDir        = "./static"
	listenAddr       = "0.0.0.0:3000"
)

func main() {
	// static server
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticDir))))

	// handlers

	// listening
	log.Printf("Starting listening on %s", listenAddr)
	log.Fatal(http.ListenAndServe(listenAddr, nil))
}

func init() {
	useTemplateCache = os.Getenv("RELOAD_TEMPLATES") != ""
	templateCache = make(map[string]*html.Template)
	templateDir = Getenv("TEMPLATE_DIR", templateDir)
	staticDir = Getenv("STATIC_DIR", staticDir)
	listenAddr = Getenv("LISTEN_ADDR", listenAddr)
}

func renderTemplate(w http.ResponseWriter, name string, data any) {
	tmpl, err := GetTemplate(name)
	if err != nil {
		log.Printf("Error getting template %s: %v", name, err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	if err = tmpl.Execute(w, data); err != nil {
		log.Printf("Error rendering template %s: %v", name, err)
	}
}

func GetTemplate(name string) (*html.Template, error) {
	if useTemplateCache {
		if tmpl, ok := templateCache[name]; ok {
			return tmpl, nil
		}
	}
	tmpl, err := loadTemplate(name)
	if err != nil {
		return nil, err
	}
	templateCache[name] = tmpl
	return tmpl, nil
}

func loadTemplate(name string) (*html.Template, error) {
	tmpls := []string{
		path.Join(templateDir, "base.html"),
		path.Join(templateDir, name),
	}
	return html.ParseFiles(tmpls...)
}

func Getenv(name, def string) string {
	if val, ok := os.LookupEnv(name); ok {
		return val
	}
	return def
}
