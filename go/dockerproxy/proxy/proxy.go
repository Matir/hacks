package proxy

import (
	"net/http"
	"net/http/httputil"
	"net/url"
)

// Middleware defines an HTTP interceptor wrapper around an http.Handler.
type Middleware func(http.Handler) http.Handler

// Proxy routes incoming client requests to the upstream Docker daemon socket.
type Proxy struct {
	upstreamAddr string
	transport    *http.Transport
	rp           *httputil.ReverseProxy
	middlewares  []Middleware
}

// New creates a new reverse proxy targeting the specified raw upstream address.
func New(upstreamAddr string) (*Proxy, error) {
	transport, err := NewTransport(upstreamAddr)
	if err != nil {
		return nil, err
	}

	// Fake URL for reverse proxy target since transport handles the actual network dialing
	targetURL, _ := url.Parse("http://docker")

	rp := httputil.NewSingleHostReverseProxy(targetURL)
	rp.Transport = transport

	return &Proxy{
		upstreamAddr: upstreamAddr,
		transport:    transport,
		rp:           rp,
	}, nil
}

// Use appends one or more middleware handlers to the proxy evaluation pipeline.
func (p *Proxy) Use(mw ...Middleware) {
	p.middlewares = append(p.middlewares, mw...)
}

// ServeHTTP handles incoming HTTP requests, session creation, middleware execution, and proxying.
func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	session := NewSession(r.RemoteAddr, p.upstreamAddr)
	r = r.WithContext(WithSession(r.Context(), session))

	var handler http.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if isUpgradeRequest(r) {
			_ = handleHijack(w, r, p.upstreamAddr)
			return
		}
		p.rp.ServeHTTP(w, r)
	})

	// Wrap handler in reverse order of registered middleware
	for i := len(p.middlewares) - 1; i >= 0; i-- {
		handler = p.middlewares[i](handler)
	}

	handler.ServeHTTP(w, r)
}
