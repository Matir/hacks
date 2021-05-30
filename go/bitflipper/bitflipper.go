package main

import (
	"fmt"
	"net"
	"os"
	"regexp"
	"strings"
)

type domainRecord struct {
	original string
	flipped  string
}

var domainRegexp *regexp.Regexp

func isValidDomain(domain string) bool {
	return domainRegexp.MatchString(domain)
}

func flipBitInString(domain string, bit int) string {
	input := []byte(domain)
	output := make([]byte, len(input))
	for i, c := range input {
		if bit/8 == i {
			output[i] = c ^ (1 << uint8(bit%8))
		} else {
			output[i] = c
		}
	}
	return string(output)
}

func processDomain(domain string, out chan<- *domainRecord) {
	for i := 0; i < len(domain)*8; i++ {
		flipped := flipBitInString(domain, i)
		if isValidDomain(flipped) {
			out <- &domainRecord{domain, flipped}
		}
	}
}

func runDNSWorker(input <-chan *domainRecord) {
	for domain := range input {
		if dns, err := net.LookupAddr(domain.flipped); err != nil {
			fmt.Fprintf(os.Stderr, "[%s]%s: %s\n", domain.original, domain.flipped, err)
		} else {
			fmt.Printf("[%s]%s: %s\n", domain.original, domain.flipped,
				strings.Join(dns, ", "))
		}
	}
}

func main() {
	out := make(chan *domainRecord, 100)
	for i := 0; i < 10; i++ {
		go runDNSWorker(out)
	}
	for _, domain := range os.Args[1:] {
		processDomain(domain, out)
	}
	close(out)
	// Start a final DNS worker
	runDNSWorker(out)
	os.Stderr.Sync()
	os.Stdout.Sync()
}

func init() {
	dr, err := regexp.Compile("^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9][a-z0-9-]*[a-z0-9])+$")
	if err == nil {
		domainRegexp = dr
	} else {
		panic(err)
	}
}
