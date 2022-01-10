package acmedns

import (
	"reflect"
	"testing"
)

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
	}
	for _, tc := range cases {
		res := domainMatches(tc.domain, tc.pattern)
		if res != tc.result {
			t.Errorf("For domain %s, pattern %s, got %v, expected %v.", tc.domain, tc.pattern, res, tc.result)
		}
	}
}
