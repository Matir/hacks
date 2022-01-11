package acmedns

import (
	"context"
	"errors"
	"log"
	"os"
	"strings"

	"golang.org/x/oauth2/google"
	"google.golang.org/api/dns/v1"
	"google.golang.org/api/googleapi"
)

const (
	dnsProjectEnv = "DNS_PROJECT"
)

var (
	ErrorNoZone      = errors.New("No zone found")
	ErrorInvalidResp = errors.New("Unexpected response")
	ErrorNotFound    = errors.New("RRSet not Found")
)

type GCPDNSProvider struct {
	service *dns.Service
	project string
}

// Credentials can be provided in env via
// GOOGLE_APPLICATION_CREDENTIALS=./dnsadmin.json
func NewGCPDNSProvider(ctx context.Context) (*GCPDNSProvider, error) {
	svc, err := dns.NewService(ctx)
	if err != nil {
		return nil, err
	}
	project, err := findProjectName(ctx)
	if err != nil {
		return nil, err
	}
	return &GCPDNSProvider{
		service: svc,
		project: project,
	}, nil
}

// Get the TXT record associated with name
// Returns an empty string if it does not exist
func (p *GCPDNSProvider) GetTXT(name string) (string, error) {
	if !strings.HasSuffix(name, ".") {
		name = name + "."
	}
	zname, err := p.findManagedZone(name)
	if err != nil {
		return "", err
	}
	rrsvc := dns.NewResourceRecordSetsService(p.service)
	resp, err := rrsvc.Get(p.project, zname, name, "TXT").Do()
	if err != nil {
		// Special case 404s
		if googleAPIErrorCode(err) == 404 {
			return "", nil
		}
		return "", err
	}
	if len(resp.Rrdatas) != 1 {
		log.Printf("Expected only one result, got: %v", resp.Rrdatas)
		return "", ErrorInvalidResp
	}
	return resp.Rrdatas[0], nil
}

func (p *GCPDNSProvider) SetTXT(name, value string) (string, error) {
	if !strings.HasSuffix(name, ".") {
		name = name + "."
	}
	zname, err := p.findManagedZone(name)
	if err != nil {
		return "", err
	}
	rrsvc := dns.NewResourceRecordSetsService(p.service)
	resp, err := rrsvc.Get(p.project, zname, name, "TXT").Do()
	save := func() (*dns.ResourceRecordSet, error) {
		return rrsvc.Patch(p.project, zname, name, "TXT", resp).Do()
	}
	if err != nil {
		if googleAPIErrorCode(err) == 404 {
			// Need to create
			resp = &dns.ResourceRecordSet{
				Name: name,
				Type: "TXT",
				Ttl:  300,
			}
			save = func() (*dns.ResourceRecordSet, error) {
				return rrsvc.Create(p.project, zname, resp).Do()
			}
		} else {
			log.Printf("Error getting existing records: %v", err)
			return "", err
		}
	}
	// Update resp
	resp.Rrdatas = []string{value}
	resp, err = save()
	if err != nil {
		return "", err
	}
	return value, nil
}

func (p *GCPDNSProvider) DeleteTXT(name string) error {
	if !strings.HasSuffix(name, ".") {
		name = name + "."
	}
	zname, err := p.findManagedZone(name)
	if err != nil {
		return err
	}
	rrsvc := dns.NewResourceRecordSetsService(p.service)
	_, err = rrsvc.Delete(p.project, zname, name, "TXT").Do()
	return err
}

// Find the name of the managed zone that handles the entry for `name`
// This will be the zone with the longest suffix matching name.
// Note that misconfigurations might lead to this being the wrong zone.
// This should work 99% of the time though.
func (p *GCPDNSProvider) findManagedZone(name string) (string, error) {
	svc := dns.NewManagedZonesService(p.service)
	zoneResp, err := svc.List(p.project).Do()
	if err != nil {
		return "", err
	}
	bestMatch := 0
	var bestZone *dns.ManagedZone
	for _, zone := range zoneResp.ManagedZones {
		zoneName := zone.DnsName
		if l := dnsMatch(zoneName, name); l > bestMatch {
			bestMatch = l
			bestZone = zone
		}
	}
	if bestZone == nil {
		log.Printf("Could not find zone for %v", name)
		return "", ErrorNoZone
	}
	zoneName := bestZone.Name
	log.Printf("Found zone %v for name %v", zoneName, name)
	return zoneName, nil
}

func dnsMatch(a, b string) int {
	aPieces := strings.Split(a, ".")
	bPieces := strings.Split(b, ".")
	l := len(aPieces)
	if len(bPieces) < l {
		l = len(bPieces)
	}
	if l == 0 {
		return 0
	}
	for i := 1; i <= l; i++ {
		if aPieces[len(aPieces)-i] != bPieces[len(bPieces)-i] {
			return i - 1
		}
	}
	return l
}

func findProjectName(ctx context.Context) (string, error) {
	if pname := os.Getenv(dnsProjectEnv); pname != "" {
		return pname, nil
	}
	creds, err := google.FindDefaultCredentials(ctx)
	if err != nil {
		return "", err
	}
	log.Printf("Found project id: %v", creds.ProjectID)
	return creds.ProjectID, nil
}

// Get the API Error code *IFF* this is a googleapi.Error
func googleAPIErrorCode(e error) int {
	if gerr, ok := e.(*googleapi.Error); ok {
		return gerr.Code
	}
	return 0
}
