package main

import (
	"bufio"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
)

type FindExpressions []string

func (e *FindExpressions) String() string {
	return strings.Join([]string(*e), ", ")
}

func (e *FindExpressions) Set(value string) error {
	if value == "" {
		return errors.New("A zero-length expression makes no sense.")
	}
	*e = append(*e, value)
	return nil
}

type SearchConfig struct {
	Expressions FindExpressions
	Filenames   []string
	Quiet       bool
}

func getSearchConfig() (*SearchConfig, error) {
	rv := &SearchConfig{}
	flag.Var(&rv.Expressions, "e", "Expression to search for.")
	flag.BoolVar(&rv.Quiet, "q", false, "Quiet mode -- only use exit code.")
	flag.Parse()
	args := flag.Args()
	if len(rv.Expressions) == 0 {
		if len(args) == 0 {
			return nil, errors.New("No patterns and no files!")
		}
		rv.Expressions = FindExpressions{args[0]}
		args = args[1:]
	}
	rv.Filenames = args
	return rv, nil
}

func findMatchingFiles(cfg *SearchConfig) ([]string, error) {
	res := make([]string, 0)
	for _, name := range cfg.Filenames {
		if ok, err := fileContainsPatterns(name, cfg.Expressions); err != nil {
			return nil, err
		} else if ok {
			res = append(res, name)
		}
	}
	return res, nil
}

func fileContainsPatterns(name string, patterns FindExpressions) (bool, error) {
	file, err := os.Open(name)
	if err != nil {
		return false, err
	}
	defer file.Close()
	return readerContainsPatterns(file, patterns)
}

func readerContainsPatterns(rdr io.Reader, patterns FindExpressions) (bool, error) {
	found := make([]bool, len(patterns))
	scanner := bufio.NewScanner(rdr)
	for scanner.Scan() {
		line := scanner.Text()
		for i, p := range patterns {
			found[i] = found[i] || strings.Contains(line, p)
		}
		if foundAll(found) {
			return true, nil
		}
	}
	if err := scanner.Err(); err != nil {
		return false, err
	}
	return foundAll(found), nil
}

func foundAll(vals []bool) bool {
	for _, v := range vals {
		if !v {
			return false
		}
	}
	return true
}

func main() {
	cfg, err := getSearchConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(2)
	}
	if len(cfg.Filenames) > 0 {
		results, err := findMatchingFiles(cfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(2)
		}
		if len(results) == 0 {
			os.Exit(1)
		}
		if !cfg.Quiet {
			for _, v := range results {
				fmt.Println(v)
			}
		}
	} else {
		res, err := readerContainsPatterns(os.Stdin, cfg.Expressions)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(2)
		}
		if res {
			if !cfg.Quiet {
				fmt.Println("stdin matches")
			}
		} else {
			os.Exit(1)
		}
	}
}
