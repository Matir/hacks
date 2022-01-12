package acmedns

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"

	"google.golang.org/api/idtoken"
)

type acmeDnsContextKey string
type domainAuthzMap map[string][]string

type DNSProvider interface {
	GetTXT(string) (string, error)
	SetTXT(string, string) (string, error)
	DeleteTXT(string) error
}

type AuthValidator interface {
	Validate(ctx context.Context, idToken string, audience string) (*idtoken.Payload, error)
}

const (
	userAuthContext = acmeDnsContextKey("user")
	DomainAuthzVar  = "DOMAIN_AUTHZ"
	acmeSubdomain   = "_acme-challenge"
)

var domainAuthzConfig domainAuthzMap
var domainAuthzLock sync.RWMutex
var defaultAuthValidator AuthValidator

var (
	ErrorMissingHeader      = errors.New("Missing Authorization Header")
	ErrorWrongAuthorization = errors.New("Wrong Authorization Type")
	ErrorNoUserInJWT        = errors.New("No user in JWT")
	ErrorNoDomain           = errors.New("No domain")
	ErrorAuthzFailed        = errors.New("Authorization failed")
)

// Main entry point for DNS Handler
func AcmeDNS(w http.ResponseWriter, r *http.Request) {
	if authz, err := getDomainAuthzConfig(); err != nil {
		log.Printf("Error loading Authz config: %v", err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	} else {
		provider, err := NewGCPDNSProvider(r.Context())
		if err != nil {
			log.Printf("Error getting GCP DNS Provider: %v", err)
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}
		acmeDNSInternal(w, r, getAuthorizedUser, authz, provider)
	}
}

// Entrypoint with injected providers for testing
func acmeDNSInternal(w http.ResponseWriter, r *http.Request, userLookup func(r *http.Request) (string, error), authz domainAuthzMap, provider DNSProvider) {
	if user, err := userLookup(r); err != nil {
		// 401, auth failed
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	} else {
		// Extract relevant data
		ctx := context.WithValue(r.Context(), userAuthContext, user)
		domain, err := getDomain(r)
		if err != nil {
			log.Printf("Request with no domain: %s", r.URL.Path)
			http.Error(w, "Bad Request", http.StatusBadRequest)
			return
		}

		// Check authz map
		if allowedPatterns, ok := authz[user]; !ok {
			log.Printf("No patterns configured for user %v, denying!", user)
			http.Error(w, "Forbidden", http.StatusForbidden)
			return
		} else {
			if !isDomainAllowed(domain, allowedPatterns) {
				log.Printf("User %v not allowed access to domain %v. (Allowed Patterns: %v)", user, domain, allowedPatterns)
				http.Error(w, "Forbidden", http.StatusForbidden)
				return
			}
		}

		if !strings.HasPrefix(domain, acmeSubdomain+".") {
			domain = acmeSubdomain + "." + domain
		}

		// Dispatch to method
		switch r.Method {
		case http.MethodGet:
			log.Printf("Lookup for domain %v, user %v.", domain, user)
			acmeDNSLookup(ctx, w, r, domain, provider)
		case http.MethodPost:
			log.Printf("Update for domain %v, user %v.", domain, user)
			acmeDNSUpdate(ctx, w, r, domain, provider)
		case http.MethodDelete:
			log.Printf("Delete for domain %v, user %v.", domain, user)
			acmeDNSDelete(ctx, w, r, domain, provider)
		default:
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}
	}
}

// Lookup the record here
func acmeDNSLookup(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string, provider DNSProvider) {
	// Expects no body.  Will return *just* the value as a string *unless*
	// application/json is in the Accept header.
	result, err := provider.GetTXT(domain)
	if err != nil {
		log.Printf("Failed doing lookup for TXT record: %v", err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	}
	// Nothing found
	if result == "" {
		http.Error(w, "Not Found", http.StatusNotFound)
		return
	}
	writeResult(w, r, domain, result)
}

func acmeDNSUpdate(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string, provider DNSProvider) {
	var record string
	if strings.HasPrefix(r.Header.Get("Content-type"), "application/json") {
		// read data from JSON
		data := struct {
			Value string `json:"value"`
		}{}
		if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
			log.Printf("Error reading JSON: %v", err)
			http.Error(w, "Bad Request", http.StatusBadRequest)
			return
		}
		record = data.Value
	} else {
		// read from form data
		record = r.FormValue("value")
	}
	if record == "" {
		log.Printf("Empty body for domain update: %v", domain)
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}
	log.Printf("Updating domain %v to %v", domain, record)
	if result, err := provider.SetTXT(domain, record); err != nil {
		log.Printf("Error updating text record (domain %v, record %v): %v", domain, record, err)
		// TODO: detect error type and give appropriate code
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	} else {
		writeResult(w, r, domain, result)
	}
}

func acmeDNSDelete(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string, provider DNSProvider) {
}

func writeResult(w http.ResponseWriter, r *http.Request, domain, result string) {
	if strings.Contains(r.Header.Get("Accept"), "application/json") {
		w.Header().Set("Content-type", "application/json")
		e := json.NewEncoder(w)
		data := struct {
			Name  string `json:"name"`
			Value string `json:"value"`
		}{
			Name:  domain,
			Value: result,
		}
		if err := e.Encode(data); err != nil {
			log.Printf("Error writing JSON data: %v", err)
		}
		return
	}
	w.Header().Set("Content-type", "text/plain")
	fmt.Fprintf(w, "%s", result)
}

func getExpectedAudience(r *http.Request) string {
	proto := "https"
	if r.Header.Get("X-Forwarded-Proto") == "http" {
		proto = "http"
	}
	return fmt.Sprintf("%s://%s/%s", proto, r.Host, os.Getenv("FUNCTION_TARGET"))
}

func getTokenFromRequest(r *http.Request) (string, error) {
	authz := r.Header.Get("Authorization")
	if authz == "" {
		return "", ErrorMissingHeader
	}
	pieces := strings.Split(authz, " ")
	if len(pieces) != 2 {
		return "", ErrorWrongAuthorization
	}
	if !strings.EqualFold("bearer", pieces[0]) {
		return "", ErrorWrongAuthorization
	}
	return pieces[1], nil
}

func getValidatedToken(ctx context.Context, r *http.Request) (*idtoken.Payload, error) {
	if tok, err := getTokenFromRequest(r); err != nil {
		return nil, err
	} else {
		return defaultAuthValidator.Validate(ctx, tok, getExpectedAudience(r))
	}
}

func getAuthorizedUser(r *http.Request) (string, error) {
	if token, err := getValidatedToken(r.Context(), r); err != nil {
		return "", err
	} else {
		if user, ok := token.Claims["email"]; ok {
			if email, ok := user.(string); ok {
				return email, nil
			}
		}
		return "", ErrorNoUserInJWT
	}
}

func getDomain(r *http.Request) (string, error) {
	for _, piece := range strings.Split(r.URL.Path, "/") {
		if piece != "" {
			return piece, nil
		}
	}
	return "", ErrorNoDomain
}

func parseDomainAuthzConfig(cfgstr string) (domainAuthzMap, error) {
	result := make(domainAuthzMap)
	for _, entry := range strings.Split(cfgstr, ";") {
		if entry == "" {
			continue
		}
		pieces := strings.SplitN(entry, "=", 2)
		if len(pieces) != 2 {
			return nil, fmt.Errorf("Missing = in authz entry: %s", entry)
		}
		key := strings.TrimSpace(pieces[0])
		if _, ok := result[key]; ok {
			return nil, fmt.Errorf("Duplicate key for authz entry: %s", entry)
		}
		result[key] = trimStringSlice(strings.Split(pieces[1], ","))
	}
	return result, nil
}

func getDomainAuthzConfig() (domainAuthzMap, error) {
	domainAuthzLock.Lock()
	defer domainAuthzLock.Unlock()
	if domainAuthzConfig == nil {
		if res, err := parseDomainAuthzConfig(os.Getenv(DomainAuthzVar)); err != nil {
			return nil, err
		} else {
			domainAuthzConfig = res
		}
	}
	return domainAuthzConfig, nil
}

func trimStringSlice(items []string) []string {
	results := make([]string, len(items))
	for i, v := range items {
		results[i] = strings.TrimSpace(v)
	}
	return results
}

// Authz tests
func isDomainAllowed(domain string, allowlist []string) bool {
	for _, pattern := range allowlist {
		if domainMatches(domain, pattern) {
			return true
		}
	}
	return false
}

// Check if domain matches pattern.
// Pattern permits wildcards as follows:
// * -> match any name in this spot (exactly 1)
// ** -> match any name in this spot and all subdomains (0 or more)
// Wildcard is only permitted as the leftmost element and *must* be the entire
// element
func domainMatches(domain, pattern string) bool {
	domain = normalizeDomain(domain)
	pattern = normalizeDomain(pattern)
	// short circuit simple cases
	if domain == pattern {
		return true
	}

	slicesMatch := func(a, b []string) bool {
		if len(a) != len(b) {
			return false
		}
		for i := 0; i < len(a); i++ {
			if a[i] != b[i] {
				return false
			}
		}
		return true
	}

	domainPieces := strings.Split(domain, ".")
	patternPieces := strings.Split(pattern, ".")
	switch patternPieces[0] {
	case "**":
		// is remaining pattern the domain suffix?
		patternPieces = patternPieces[1:]
		if len(patternPieces) > len(domainPieces) {
			return false
		}
		domainPieces = domainPieces[len(domainPieces)-len(patternPieces):]
		return slicesMatch(patternPieces, domainPieces)
	case "*":
		// is remaining pattern the domain suffix with same number of elements?
		if len(domainPieces) != len(patternPieces) {
			return false
		}
		return slicesMatch(patternPieces[1:], domainPieces[1:])
	default:
		// No wildcards, should have matched exact match
		return false
	}
}

// Normalize a domain by removing a trailing . and a leading _acme-challenge.
func normalizeDomain(domain string) string {
	return strings.ToLower(strings.Trim(strings.TrimPrefix(domain, acmeSubdomain+"."), "."))
}

func init() {
	val, err := idtoken.NewValidator(context.Background())
	if err != nil {
		panic(err)
	}
	defaultAuthValidator = val
}
