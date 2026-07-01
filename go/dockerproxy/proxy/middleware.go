package proxy

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"regexp"
	"strconv"
	"strings"

	"github.com/Matir/hacks/go/dockerproxy/rules"
)

type filteringResponseWriter struct {
	http.ResponseWriter
	statusCode int
	body       bytes.Buffer
}

func (fw *filteringResponseWriter) WriteHeader(code int) {
	fw.statusCode = code
}

func (fw *filteringResponseWriter) Write(b []byte) (int, error) {
	if fw.statusCode == 0 {
		fw.statusCode = http.StatusOK
	}
	return fw.body.Write(b)
}

// RuleEvaluator returns a middleware that evaluates incoming requests against the policy ruleset.
// Denied requests are blocked with HTTP 403 Forbidden. Response list requests are transparently filtered.
func RuleEvaluator(rs *rules.Ruleset) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if rs == nil {
				next.ServeHTTP(w, r)
				return
			}

			var bodySnippet []byte
			if r.Body != nil && r.ContentLength != 0 {
				bodySnippet, _ = io.ReadAll(io.LimitReader(r.Body, 65536))
				// Restore request body so downstream proxy can still read it
				r.Body = io.NopCloser(io.MultiReader(bytes.NewReader(bodySnippet), r.Body))
			}

			uri := r.URL.RequestURI()
			if uri == "" {
				uri = r.URL.Path
			}

			action, msg, ruleID := rules.Evaluate(r.Method, uri, bodySnippet, rs)
			if action == rules.ActionDeny {
				if msg == "" {
					msg = "Forbidden by security policy ruleset"
				}
				http.Error(w, msg, http.StatusForbidden)
				return
			}

			// Check if response list filtering applies
			var filterRule *rules.ResponseFilterRule
			if action == rules.ActionFilter {
				for _, rl := range rs.Rules {
					if rl.ID == ruleID && rl.ResponseFilter != nil {
						filterRule = rl.ResponseFilter
						break
					}
				}
			}
			if filterRule == nil {
				for _, rl := range rs.Rules {
					if rl.ResponseFilter != nil && rl.Action == rules.ActionFilter {
						if rl.PathPattern == "" || matchesPath(uri, rl.PathPattern) {
							filterRule = rl.ResponseFilter
							break
						}
					}
				}
			}

			if filterRule != nil && rules.IdentifyCommandType(r.Method, uri) == "list" {
				fw := &filteringResponseWriter{ResponseWriter: w}
				next.ServeHTTP(fw, r)

				if fw.statusCode != http.StatusOK {
					w.WriteHeader(fw.statusCode)
					_, _ = w.Write(fw.body.Bytes())
					return
				}

				filteredBytes := filterListPayload(uri, fw.body.Bytes(), filterRule)
				w.Header().Set("Content-Length", strconv.Itoa(len(filteredBytes)))
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusOK)
				_, _ = w.Write(filteredBytes)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func matchesPath(uri, pattern string) bool {
	re, err := regexp.Compile(pattern)
	return err == nil && re.MatchString(uri)
}

func filterListPayload(uri string, payload []byte, rf *rules.ResponseFilterRule) []byte {
	if strings.Contains(uri, "/containers/json") {
		var containers []rules.ContainerSummary
		if err := json.Unmarshal(payload, &containers); err != nil {
			return payload
		}
		var filtered []rules.ContainerSummary
		for _, c := range containers {
			if matchesFilterContainer(&c, rf) {
				filtered = append(filtered, c)
			}
		}
		if filtered == nil {
			filtered = []rules.ContainerSummary{}
		}
		out, _ := json.Marshal(filtered)
		return out
	}

	if strings.Contains(uri, "/images/json") {
		var images []rules.ImageSummary
		if err := json.Unmarshal(payload, &images); err != nil {
			return payload
		}
		var filtered []rules.ImageSummary
		for _, img := range images {
			if matchesFilterImage(&img, rf) {
				filtered = append(filtered, img)
			}
		}
		if filtered == nil {
			filtered = []rules.ImageSummary{}
		}
		out, _ := json.Marshal(filtered)
		return out
	}

	return payload
}

func matchesFilterContainer(c *rules.ContainerSummary, rf *rules.ResponseFilterRule) bool {
	if len(rf.AllowedNames) > 0 {
		nameMatched := false
		for _, n := range c.Names {
			cleanName := strings.TrimPrefix(n, "/")
			for _, p := range rf.AllowedNames {
				re, err := regexp.Compile(p)
				if err == nil && (re.MatchString(n) || re.MatchString(cleanName)) {
					nameMatched = true
					break
				}
			}
			if nameMatched {
				break
			}
		}
		if !nameMatched {
			return false
		}
	}

	if len(rf.AllowedLabels) > 0 {
		for k, v := range rf.AllowedLabels {
			if c.Labels == nil || c.Labels[k] != v {
				return false
			}
		}
	}

	return true
}

func matchesFilterImage(img *rules.ImageSummary, rf *rules.ResponseFilterRule) bool {
	if len(rf.AllowedNames) > 0 {
		nameMatched := false
		for _, tag := range img.RepoTags {
			for _, p := range rf.AllowedNames {
				re, err := regexp.Compile(p)
				if err == nil && re.MatchString(tag) {
					nameMatched = true
					break
				}
			}
			if nameMatched {
				break
			}
		}
		if !nameMatched {
			return false
		}
	}

	if len(rf.AllowedLabels) > 0 {
		for k, v := range rf.AllowedLabels {
			if img.Labels == nil || img.Labels[k] != v {
				return false
			}
		}
	}

	return true
}
