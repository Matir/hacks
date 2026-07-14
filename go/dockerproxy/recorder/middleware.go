package recorder

import (
	"bufio"
	"bytes"
	"io"
	"net"
	"net/http"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/proxy"
)

type responseWriter struct {
	http.ResponseWriter
	statusCode int
	body       bytes.Buffer
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	if rw.statusCode == 0 {
		rw.statusCode = http.StatusOK
	}
	if rw.body.Len() < 65536 {
		remaining := 65536 - rw.body.Len()
		if len(b) > remaining {
			rw.body.Write(b[:remaining])
		} else {
			rw.body.Write(b)
		}
	}
	return rw.ResponseWriter.Write(b)
}

func (rw *responseWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	if hijacker, ok := rw.ResponseWriter.(http.Hijacker); ok {
		return hijacker.Hijack()
	}
	return nil, nil, http.ErrNotSupported
}

// Middleware creates an HTTP handler wrapper that records transactions to the given Writer.
func Middleware(writer *Writer) proxy.Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if writer == nil {
				next.ServeHTTP(w, r)
				return
			}

			// Capture request body snippet bounded at 64KB
			var reqBodySnippet []byte
			if r.Body != nil {
				reqBodySnippet, _ = io.ReadAll(io.LimitReader(r.Body, 65536))
				r.Body = io.NopCloser(io.MultiReader(bytes.NewReader(reqBodySnippet), r.Body))
			}

			rw := &responseWriter{ResponseWriter: w, statusCode: 200}

			next.ServeHTTP(rw, r)

			session, _ := proxy.FromContext(r.Context())
			sessionID := "anonymous"
			if session != nil {
				sessionID = session.ID
			}

			rec := &TrafficRecord{
				SessionID:       sessionID,
				Timestamp:       time.Now().UTC().Format(time.RFC3339),
				Method:          r.Method,
				URI:             r.URL.RequestURI(),
				ClientHeaders:   r.Header,
				RequestBody:     string(reqBodySnippet),
				StatusCode:      rw.statusCode,
				ResponseHeaders: rw.Header(),
				ResponseBody:    rw.body.String(),
				Outcome:         "allowed",
				MatchedRuleID:   "default",
			}
			if rw.statusCode == http.StatusForbidden {
				rec.Outcome = "denied"
			}

			_ = writer.WriteRecord(rec)
		})
	}
}
