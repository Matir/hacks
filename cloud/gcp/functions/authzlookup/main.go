package authzlookup

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"

	"google.golang.org/api/idtoken"
)

var (
	ErrorMissingHeader      = errors.New("Missing Authorization Header")
	ErrorWrongAuthorization = errors.New("Wrong Authorization Type")
	ErrorNoUserInJWT        = errors.New("No user in JWT")
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
	// TODO: add audience assertion
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

func AuthzLookup(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Host: %s\n", r.Host)
	fmt.Fprintf(w, "Path: %s\n", r.URL.Path)
	if tok, err := getValidatedToken(r.Context(), r); err != nil {
		fmt.Fprintf(w, "Error: %s\n", err)
	} else {
		fmt.Fprintf(w, "Token: %+v\n", tok)
	}
	fmt.Fprintf(w, "Environ: %v\n", os.Environ())
	user, err := getAuthorizedUser(r)
	if err != nil {
		fmt.Fprintf(w, "Error: %s\n", err)
	} else {
		fmt.Fprintf(w, "User: %s\n", user)
	}
}
