package acmedns

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"

	"google.golang.org/api/idtoken"
)

type acmeDnsContextKey string
type domainAuthzMap map[string][]string

const (
	userAuthContext = acmeDnsContextKey("user")
	DomainAuthzVar  = "DOMAIN_AUTHZ"
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

func AcmeDNS(w http.ResponseWriter, r *http.Request) {
	if user, err := getAuthorizedUser(r); err != nil {
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

func getDomainAuthzConfig() (domainAuthzMap, error) {
	domainAuthzLock.Lock()
	defer domainAuthzLock.Unlock()
	if domainAuthzConfig == nil {
		domainAuthzConfig = make(domainAuthzMap)
		for _, entry := range strings.Split(os.GetEnv(DomainAuthzVar), ";") {
			pieces := strings.SplitN(entry, "=", 2)
			if len(pieces) != 2 {
				return nil, fmt.Errorf("Missing = in authz entry: %s", entry)
			}
			if _, ok := domainAuthzConfig[pieces[0]]; ok {
				return nil, fmt.Errorf("Duplicate key for authz entry: %s", entry)
			}
			domainAuthzConfig[pieces[0]] = strings.Split(pieces[1], ",")
		}
	}
	return domainAuthzConfig, nil
}
