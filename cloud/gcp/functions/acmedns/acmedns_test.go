package acmedns

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"reflect"
	"testing"

	"google.golang.org/api/idtoken"
)

func TestGetExpectedAudience(t *testing.T) {
	cases := []struct {
		proto  string
		host   string
		target string
		result string
	}{
		{"https", "example.org", "foobar", "https://example.org/foobar"},
		{"http", "example.com", "foobaz", "http://example.com/foobaz"},
		{"", "example.com", "bang", "https://example.com/bang"},
	}
	for _, c := range cases {
		os.Setenv("FUNCTION_TARGET", c.target)
		r := httptest.NewRequest("GET", fmt.Sprintf("http://%s/%s", c.host, c.target), nil)
		r.Header.Set("X-Forwarded-Proto", c.proto)
		if getExpectedAudience(r) != c.result {
			t.Fatalf("Expected %v, got %v", c.result, getExpectedAudience(r))
		}
	}
}

func TestGetTokenFromRequest(t *testing.T) {
	tokVal := "abcdefghi"
	cases := []struct {
		include  bool
		value    string
		expected string
		expError error
	}{
		{true, fmt.Sprintf("Bearer %s", tokVal), tokVal, nil},
		{true, fmt.Sprintf("bearer %s", tokVal), tokVal, nil},
		{false, "", "", ErrorMissingHeader},
		{true, "", "", ErrorMissingHeader},
		{true, "hello world", "", ErrorWrongAuthorization},
		{true, "a b c d e f", "", ErrorWrongAuthorization},
	}
	for _, c := range cases {
		r := httptest.NewRequest("GET", "/", nil)
		if c.include {
			r.Header.Set("Authorization", c.value)
		}
		authz, err := getTokenFromRequest(r)
		if authz != c.expected {
			t.Fatalf("Got token %v, expected %v", authz, c.expected)
		}
		if err != c.expError {
			t.Fatalf("Got error %v, expected %v", err, c.expError)
		}
	}
}

func TestGetDomain(t *testing.T) {
	cases := []struct {
		path     string
		domain   string
		expError error
	}{
		{"/example.com/", "example.com", nil},
		{"/foo.bar.example.com/more/args/on/this", "foo.bar.example.com", nil},
		{"/", "", ErrorNoDomain},
	}
	for _, c := range cases {
		r := httptest.NewRequest("GET", c.path, nil)
		res, err := getDomain(r)
		if res != c.domain {
			t.Fatalf("Expected domain %v, got %v", c.domain, res)
		}
		if err != c.expError {
			t.Fatalf("Exepcted error %v, got %v", c.expError, err)
		}
	}
}

func TestParseDomainAuthzConfig(t *testing.T) {
	expected := domainAuthzMap{
		"user1@domain1.com": []string{"**.domain1.com"},
		"user2@domain2.com": []string{"abc.domain2.com", "def.domain2.com"},
	}
	// A few different representations
	cfgstrs := []string{
		"user1@domain1.com=**.domain1.com;user2@domain2.com=abc.domain2.com,def.domain2.com",
		"user1@domain1.com=**.domain1.com; user2@domain2.com=abc.domain2.com, def.domain2.com",
		"user1@domain1.com = **.domain1.com; user2@domain2.com = abc.domain2.com, def.domain2.com;",
	}
	for _, cfgstr := range cfgstrs {
		res, err := parseDomainAuthzConfig(cfgstr)
		if err != nil {
			t.Fatalf("Unexpected error: %s", err)
		}
		if !reflect.DeepEqual(expected, res) {
			t.Fatalf("%v != %v", expected, res)
		}
	}
	broken := []string{
		"user1@domain.com;user2@domain.com=abc.domain2.com",
		"user1@domain.com=**.domain1.com;user1@domain.com=*.domain.com",
	}
	for _, cfgstr := range broken {
		res, err := parseDomainAuthzConfig(cfgstr)
		if res != nil {
			t.Fatalf("Expected nil map for cfgstr: %v", cfgstr)
		}
		if err == nil {
			t.Fatalf("Expected non-nil error for cfgstr: %v", cfgstr)
		}
	}
}

func TestDomainMatches(t *testing.T) {
	cases := []struct {
		domain  string
		pattern string
		result  bool
	}{
		{"test.domain.com", "*.domain.com", true},
		{"test.domain.com", "**.domain.com", true},
		{"testdomain.com", "*.domain.com", false},
		{"testdomain.com", "**.domain.com", false},
		{"a.b.domain.com", "*.domain.com", false},
		{"a.b.domain.com", "**.domain.com", true},
		{"domain.com", "*.domain.com", false},
		{"domain.com", "**.domain.com", true},
		{"test.domain.com.", "*.domain.com", true},
		{"test.domain.com", "test.domain.com.", true},
		{"TEST.DOMAIN.COM", "*.domain.com.", true},
		{"_acme-challenge.domain.com", "*.domain.com", false},
		{"_acme-challenge.test.domain.com", "*.domain.com", true},
		{"_acme-challenge.test.domain.com.", "**.domain.com.", true},
		{"_acme-challenge.domain.com.", "**.domain.com.", true},
		{"foo.domain.com", "bar.domain.com", false},
		{"foo.domain.com", "**.domain2.com", false},
		{"domain.com", "**.foo.bar.baz.domain.com", false},
	}
	for _, tc := range cases {
		res := domainMatches(tc.domain, tc.pattern)
		if res != tc.result {
			t.Errorf("For domain %s, pattern %s, got %v, expected %v.", tc.domain, tc.pattern, res, tc.result)
		}
	}
}

func TestAcmeDNSInternal_Update_JSON(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "test@example.com", nil
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	json.NewEncoder(&buf).Encode(struct {
		Value string `json:"value"`
	}{
		Value: token,
	})
	req := httptest.NewRequest(http.MethodPost, fmt.Sprintf("/%s", domain), &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Content-type", "application/json")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("Expected OK, got %v", resp.StatusCode)
	}
	respData := struct {
		Value string `json:"value"`
		Name  string `json:"name"`
	}{}
	if err := json.NewDecoder(resp.Body).Decode(&respData); err != nil {
		t.Fatalf("Error reading JSON response: %v", err)
	}
	if respData.Value != token {
		t.Fatalf("Expected token %v, got %v", token, respData.Value)
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if respData.Name != acmeDomain {
		t.Fatalf("Expected name %v, got %v", acmeDomain, respData.Name)
	}
	if v, ok := provider.data[acmeDomain]; !ok {
		t.Fatalf("Value not stored in provider!")
	} else {
		if v != token {
			t.Fatalf("Expected stored token %v, got %v", token, v)
		}
	}
}

func TestAcmeDNSInternal_Update_URLEncoded(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "test@example.com", nil
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	vals := url.Values{}
	vals.Add("value", token)
	fmt.Fprintf(&buf, "%s", vals.Encode())
	req := httptest.NewRequest(http.MethodPost, fmt.Sprintf("/%s", domain), &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Content-type", "application/x-www-form-urlencoded")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("Expected OK, got %v", resp.StatusCode)
	}
	if respBuf, err := ioutil.ReadAll(resp.Body); err != nil {
		t.Fatalf("Error reading body: %v", err)
	} else {
		if string(respBuf) != token {
			t.Fatalf("Expected token %v, got %v", token, string(respBuf))
		}
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if v, ok := provider.data[acmeDomain]; !ok {
		t.Fatalf("Value not stored in provider!")
	} else {
		if v != token {
			t.Fatalf("Expected stored token %v, got %v", token, v)
		}
	}
}

func TestAcmeDNSInternal_Update_NoUser(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "", fmt.Errorf("Failed to find user!")
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	vals := url.Values{}
	vals.Add("value", token)
	fmt.Fprintf(&buf, "%s", vals.Encode())
	req := httptest.NewRequest(http.MethodPost, fmt.Sprintf("/%s", domain), &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Content-type", "application/x-www-form-urlencoded")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("Expected Unauthorized Status (%v), got %v", http.StatusUnauthorized, resp.StatusCode)
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if _, ok := provider.data[acmeDomain]; ok {
		t.Fatalf("Record updated when no record expected!")
	}
	if len(provider.data) != 0 {
		t.Fatalf("Record updated when no record expected: %v", provider.data)
	}
}

func TestAcmeDNSInternal_Update_NoDomain(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "test@example.com", nil
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	vals := url.Values{}
	vals.Add("value", token)
	fmt.Fprintf(&buf, "%s", vals.Encode())
	req := httptest.NewRequest(http.MethodPost, "/", &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Content-type", "application/x-www-form-urlencoded")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("Expected Bad Request Status (%v), got %v", http.StatusUnauthorized, resp.StatusCode)
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if _, ok := provider.data[acmeDomain]; ok {
		t.Fatalf("Record updated when no record expected!")
	}
	if len(provider.data) != 0 {
		t.Fatalf("Record updated when no record expected: %v", provider.data)
	}
}

func TestAcmeDNSInternal_Update_BadDomain(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "test2@example.com", nil
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	vals := url.Values{}
	vals.Add("value", token)
	fmt.Fprintf(&buf, "%s", vals.Encode())
	req := httptest.NewRequest(http.MethodPost, fmt.Sprintf("/%s", domain), &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Content-type", "application/x-www-form-urlencoded")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusForbidden {
		t.Fatalf("Expected Forbidden Status (%v), got %v", http.StatusForbidden, resp.StatusCode)
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if _, ok := provider.data[acmeDomain]; ok {
		t.Fatalf("Record updated when no record expected!")
	}
	if len(provider.data) != 0 {
		t.Fatalf("Record updated when no record expected: %v", provider.data)
	}
}

func TestAcmeDNSInternal_Update_UnknownUser(t *testing.T) {
	userLookup := func(r *http.Request) (string, error) {
		return "nonexist@example.com", nil
	}
	buf := bytes.Buffer{}
	domain := "foo.bar.example.com"
	token := "abcdefghi"
	vals := url.Values{}
	vals.Add("value", token)
	fmt.Fprintf(&buf, "%s", vals.Encode())
	req := httptest.NewRequest(http.MethodPost, fmt.Sprintf("/%s", domain), &buf)
	rec := httptest.NewRecorder()
	req.Header.Set("Content-type", "application/x-www-form-urlencoded")
	provider := NewStubDNSProvider()
	acmeDNSInternal(rec, req, userLookup, getTestDomainAuthzMap(), provider)
	resp := rec.Result()
	if resp.StatusCode != http.StatusForbidden {
		t.Fatalf("Expected Forbidden Status (%v), got %v", http.StatusForbidden, resp.StatusCode)
	}
	acmeDomain := fmt.Sprintf("_acme-challenge.%s", domain)
	if _, ok := provider.data[acmeDomain]; ok {
		t.Fatalf("Record updated when no record expected!")
	}
	if len(provider.data) != 0 {
		t.Fatalf("Record updated when no record expected: %v", provider.data)
	}
}

func getTestDomainAuthzMap() domainAuthzMap {
	return domainAuthzMap{
		"test@example.com":  []string{"**.example.com"},
		"test2@example.com": []string{"test2.example.com"},
	}
}

type StubValidator struct {
	email string
	err   error
}

func (v *StubValidator) Validate(_ context.Context, token, _ string) (*idtoken.Payload, error) {
	if v.err != nil {
		return nil, v.err
	}
	if token == "noemail" {
		return &idtoken.Payload{
			Claims: map[string]interface{}{},
		}, nil
	}
	if token != v.email {
		return nil, fmt.Errorf("Invalid token")
	}
	return &idtoken.Payload{
		Claims: map[string]interface{}{
			"email": v.email,
		},
	}, nil
}

func TestGetAuthorizedUser(t *testing.T) {
	oldDefaultValidator := defaultAuthValidator
	defer func() {
		defaultAuthValidator = oldDefaultValidator
	}()
	username := "foo@example.com"
	defaultAuthValidator = &StubValidator{
		email: "foo@example.com",
		err:   nil,
	}

	r := httptest.NewRequest("GET", "/", nil)
	r.Header.Set("Authorization", fmt.Sprintf("bearer %s", username))
	user, err := getAuthorizedUser(r)
	if user != username {
		t.Fatalf("Expected username %v, got %v", username, user)
	}
	if err != nil {
		t.Fatalf("Expected nil error, got %v", err)
	}

	r = httptest.NewRequest("GET", "/", nil)
	r.Header.Set("Authorization", fmt.Sprintf("bearer %s", "notuser"))
	user, err = getAuthorizedUser(r)
	if user != "" {
		t.Fatalf("Expected no username, got %v", user)
	}
	if err == nil {
		t.Fatalf("Expected error, got nil")
	}

	r = httptest.NewRequest("GET", "/", nil)
	user, err = getAuthorizedUser(r)
	if user != "" {
		t.Fatalf("Expected no username, got %v", user)
	}
	if err == nil {
		t.Fatalf("Expected error, got nil")
	}

	r = httptest.NewRequest("GET", "/", nil)
	r.Header.Set("Authorization", fmt.Sprintf("bearer %s", "noemail"))
	user, err = getAuthorizedUser(r)
	if user != "" {
		t.Fatalf("Expected no username, got %v", user)
	}
	if err != ErrorNoUserInJWT {
		t.Fatalf("Expected error ErrorNoUserInJWT, got %v", err)
	}
}
