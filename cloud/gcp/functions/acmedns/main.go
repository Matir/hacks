package acmedns

import (
	"context"
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

const (
	userAuthContext = acmeDnsContextKey("user")
	DomainAuthzVar  = "DOMAIN_AUTHZ"
	acmeSubdomain   = "_acme-challenge"
)

var domainAuthzConfig domainAuthzMap
var domainAuthzLock sync.RWMutex

var (
	ErrorMissingHeader      = errors.New("Missing Authorization Header")
	ErrorWrongAuthorization = errors.New("Wrong Authorization Type")
	ErrorNoUserInJWT        = errors.New("No user in JWT")
	ErrorNoDomain           = errors.New("No domain")
	ErrorAuthzFailed        = errors.New("Authorization failed")
)

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
		return idtoken.Validate(ctx, tok, getExpectedAudience(r))
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

// Main entry point for DNS Handler
func AcmeDNS(w http.ResponseWriter, r *http.Request) {
	if authz, err := getDomainAuthzConfig(); err != nil {
		log.Printf("Error loading Authz config: %v", err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		return
	} else {
		acmeDNSInternal(w, r, getAuthorizedUser, authz)
	}
}

// Entrypoint with injected providers for testing
func acmeDNSInternal(w http.ResponseWriter, r *http.Request, userLookup func(r *http.Request) (string, error), authz domainAuthzMap) {
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

		// Dispatch to method
		switch r.Method {
		case http.MethodGet:
			acmeDNSLookup(ctx, w, r, domain)
		case http.MethodPost:
			acmeDNSUpdate(ctx, w, r, domain)
		case http.MethodDelete:
			acmeDNSDelete(ctx, w, r, domain)
		default:
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}
	}
}

func acmeDNSLookup(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string) {
}

func acmeDNSUpdate(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string) {
}

func acmeDNSDelete(ctx context.Context, w http.ResponseWriter, r *http.Request, domain string) {
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
