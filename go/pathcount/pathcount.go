package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path"
	"sort"
	"strings"
)

type Counter struct {
	counts map[string]int
}

func main() {
	ctr := NewCounter()
	if len(os.Args) > 1 {
		ctr.countFiles(os.Args[1:])
	} else {
		ctr.readAndCount(os.Stdin)
	}
	ctr.printPaths(os.Stdout)
}

func NewCounter() *Counter {
	return &Counter{
		counts: make(map[string]int),
	}
}

func (c *Counter) countFiles(files []string) error {
	for _, f := range files {
		if fp, err := os.Open(f); err != nil {
			return fmt.Errorf("Error opening %s: %w", f, err)
		} else {
			defer fp.Close()
			if err := c.readAndCount(fp); err != nil {
				return fmt.Errorf("Error reading %s: %w", f, err)
			}
		}
	}
	return nil
}

func (c *Counter) readAndCount(rdr io.Reader) error {
	scanner := bufio.NewScanner(rdr)
	for scanner.Scan() {
		line := scanner.Text()
		c.addPaths(strings.TrimSpace(line))
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	return nil
}

func (c *Counter) addPaths(line string) {
	for line != "" {
		dir := path.Dir(line)
		if dir == line {
			break
		}
		c.counts[dir] += 1
		line = dir
	}
}

type countSortElem struct {
	counts int
	name   string
}
type countSorter []countSortElem

func (c *Counter) printPaths(w io.Writer) {
	srt := make(countSorter, 0, len(c.counts))
	for k, v := range c.counts {
		srt = append(srt, countSortElem{counts: v, name: k})
	}
	sort.Sort(srt)
	max := 0
	for _, v := range srt {
		if v.counts > max {
			max = v.counts
		}
	}
	l := len(fmt.Sprintf("%d", max))
	for _, v := range srt {
		fmt.Fprintf(w, "%*d %s\n", l, v.counts, v.name)
	}
}

func (s countSorter) Len() int {
	return len(s)
}

func (s countSorter) Less(i, j int) bool {
	return s[i].counts < s[j].counts
}

func (s countSorter) Swap(i, j int) {
	s[i], s[j] = s[j], s[i]
}
