package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/matir/hacks/go/mdtool/converter"
	"github.com/matir/hacks/go/mdtool/server"
	"github.com/spf13/cobra"
)

var (
	cssPath     string
	noHighlight bool
	noMermaid   bool
	listenAddr  string
	onlyMD      bool
	watch       bool
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "mdtool [flags] <inpath> [outpath]",
		Short: "mdtool is a tool for rendering markdown files as HTML",
		Args:  cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			// Legacy/Default Batch mode
			if len(args) < 1 {
				return cmd.Help()
			}
			c := getConverter()
			inPath := args[0]
			var outPath string
			if len(args) > 1 {
				outPath = args[1]
			}
			if watch {
				return watchBatch(c, inPath, outPath)
			}
			return runBatch(c, inPath, outPath)
		},
	}

	var convertCmd = &cobra.Command{
		Use:   "convert <inpath> [outpath]",
		Short: "Batch convert Markdown files to HTML",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			c := getConverter()
			inPath := args[0]
			var outPath string
			if len(args) > 1 {
				outPath = args[1]
			}
			if watch {
				return watchBatch(c, inPath, outPath)
			}
			return runBatch(c, inPath, outPath)
		},
	}

	var serveCmd = &cobra.Command{
		Use:   "serve [directory]",
		Short: "Run a local webserver to serve Markdown files as HTML",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			dir := "."
			if len(args) > 0 {
				dir = args[0]
			}
			c := getConverter()
			c.Watch = watch
			s := server.New(dir, listenAddr, onlyMD, c)
			s.Watch = watch
			return s.Serve()
		},
	}

	rootCmd.PersistentFlags().StringVar(&cssPath, "css", "", "Path to custom CSS file to inline")
	rootCmd.PersistentFlags().BoolVar(&noHighlight, "no-highlight", false, "Disable syntax highlighting")
	rootCmd.PersistentFlags().BoolVar(&noMermaid, "no-mermaid", false, "Disable Mermaid.js diagrams")
	rootCmd.PersistentFlags().BoolVarP(&watch, "watch", "w", false, "Watch for changes and re-convert or auto-reload")

	serveCmd.Flags().StringVarP(&listenAddr, "listen", "l", "127.0.0.1:7768", "Listen address for server")
	serveCmd.Flags().BoolVar(&onlyMD, "only-md", false, "Only serve .md files in server mode")

	rootCmd.AddCommand(convertCmd, serveCmd)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func getConverter() *converter.Converter {
	var css string
	if cssPath != "" {
		data, err := os.ReadFile(cssPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error reading CSS file: %v\n", err)
			os.Exit(1)
		}
		css = string(data)
	}
	c := converter.New(css, !noHighlight, !noMermaid)
	c.Watch = watch
	return c
}

func watchBatch(c *converter.Converter, inPath, outPath string) error {
	// Initial conversion
	if err := runBatch(c, inPath, outPath); err != nil {
		log.Printf("Initial conversion error: %v", err)
	}

	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	defer watcher.Close()

	// Watch input directory/file
	info, err := os.Stat(inPath)
	if err != nil {
		return err
	}

	if info.IsDir() {
		filepath.Walk(inPath, func(path string, info os.FileInfo, err error) error {
			if err == nil && info.IsDir() {
				watcher.Add(path)
			}
			return nil
		})
	} else {
		watcher.Add(filepath.Dir(inPath))
	}

	fmt.Printf("Watching %s for changes...\n", inPath)

	// Debounce timer
	var timer *time.Timer
	const delay = 100 * time.Millisecond

	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				return nil
			}
			if event.Op&(fsnotify.Write|fsnotify.Create) != 0 {
				if strings.HasSuffix(event.Name, ".md") {
					if timer != nil {
						timer.Stop()
					}
					timer = time.AfterFunc(delay, func() {
						fmt.Printf("Change detected in %s, re-converting...\n", event.Name)
						if err := runBatch(c, inPath, outPath); err != nil {
							log.Printf("Re-conversion error: %v", err)
						}
					})
				}
			}
		case err, ok := <-watcher.Errors:
			if !ok {
				return nil
			}
			log.Printf("Watcher error: %v", err)
		}
	}
}

func runBatch(c *converter.Converter, inPath, outPath string) error {
	info, err := os.Stat(inPath)
	if err != nil {
		return err
	}

	if info.IsDir() {
		return convertDir(c, inPath, outPath)
	}
	return convertFile(c, inPath, outPath)
}

func convertFile(c *converter.Converter, inPath, outPath string) error {
	if outPath == "" {
		outPath = strings.TrimSuffix(inPath, filepath.Ext(inPath)) + ".html"
	} else {
		outInfo, err := os.Stat(outPath)
		if err == nil && outInfo.IsDir() {
			outPath = filepath.Join(outPath, strings.TrimSuffix(filepath.Base(inPath), filepath.Ext(inPath))+".html")
		}
	}

	return doConvert(c, inPath, outPath)
}

func convertDir(c *converter.Converter, inPath, outPath string) error {
	if outPath != "" {
		if err := os.MkdirAll(outPath, 0755); err != nil {
			return err
		}
	}

	return filepath.Walk(inPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || !strings.HasSuffix(strings.ToLower(path), ".md") {
			return nil
		}

		var target string
		rel, _ := filepath.Rel(inPath, path)
		if outPath == "" {
			target = strings.TrimSuffix(path, filepath.Ext(path)) + ".html"
		} else {
			target = filepath.Join(outPath, strings.TrimSuffix(rel, filepath.Ext(rel))+".html")
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}
		}

		fmt.Printf("Converting %s -> %s\n", path, target)
		return doConvert(c, path, target)
	})
}

func doConvert(c *converter.Converter, in, out string) error {
	fIn, err := os.Open(in)
	if err != nil {
		return err
	}
	defer fIn.Close()

	fOut, err := os.Create(out)
	if err != nil {
		return err
	}
	defer fOut.Close()

	return c.Convert(fIn, fOut)
}
