package main

import (
	"encoding/hex"
	"flag"
	"log"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/miekg/dns"
)

type DNSServerOption func(*DNSServer) error

const (
	REFLECT_DNS = "me"
	DNS_TTL     = 1
)

func main() {
	addr := flag.String("addr", ":domain", "Address to listen on.")
	protoFlag := flag.String("proto", "", "Limit to only TCP or UDP")
	domain := flag.String("domain", "", "Domain under which to serve.  If not set, only considers first name.")
	flag.Parse()

	opts := make([]DNSServerOption, 0)

	switch *protoFlag {
	case "udp":
		opts = append(opts, WithUDPServer)
	case "tcp":
		opts = append(opts, WithTCPServer)
	case "", "tcp+udp", "udp+tcp":
		opts = append(opts, WithTCPServer, WithUDPServer)
	default:
		log.Fatalf("Unknown protocol: %s, must be tcp, udp, or empty for both.", *protoFlag)
	}

	if *domain != "" {
	}

	if srv, err := NewDNSServer(*addr, opts...); err != nil {
		log.Fatalf("Fatal error setting up DNSServer: %v", err)
	} else {
		go func() {
			WaitForSIGINT()
			log.Printf("Stopping server.")
			srv.Stop()
		}()
		if err := srv.ListenAndServe(); err != nil {
			log.Fatalf("Error serving: %s", err)
		}
	}
}

func WaitForSIGINT() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, syscall.SIGINT)
	<-c
}

type DNSServer struct {
	addr      string
	udpServer *dns.Server
	tcpServer *dns.Server
	withTcp   bool
	withUdp   bool
	domain    string
}

func NewDNSServer(addr string, opts ...DNSServerOption) (*DNSServer, error) {
	rv := &DNSServer{
		addr: addr,
	}
	for _, o := range opts {
		if err := o(rv); err != nil {
			return nil, err
		}
	}
	return rv, nil
}

func (s *DNSServer) ListenAndServe() error {
	c := make(chan error, 2)
	if s.withUdp {
		s.udpServer = &dns.Server{
			Addr:      s.addr,
			Net:       "udp",
			ReusePort: true,
			Handler:   s,
		}
		go func() {
			log.Printf("Starting UDP Server on %s", s.addr)
			c <- s.udpServer.ListenAndServe()
		}()
	}
	if s.withTcp {
		s.tcpServer = &dns.Server{
			Addr:      s.addr,
			Net:       "tcp",
			ReusePort: true,
			Handler:   s,
		}
		go func() {
			log.Printf("Starting TCP Server on %s", s.addr)
			c <- s.tcpServer.ListenAndServe()
		}()
	}
	return <-c
}

func (s *DNSServer) Stop() {
	if s.udpServer != nil {
		s.udpServer.Shutdown()
	}
	if s.tcpServer != nil {
		s.tcpServer.Shutdown()
	}
}

func SendError(w dns.ResponseWriter, r *dns.Msg, code int) {
	m := new(dns.Msg)
	m.SetRcode(r, code)
	w.WriteMsg(m)
}

func (s *DNSServer) ServeDNS(w dns.ResponseWriter, r *dns.Msg) {
	log.Printf("Received request from %s", w.RemoteAddr().String())
	if len(r.Question) != 1 {
		SendError(w, r, dns.RcodeRefused)
		return
	}
	q := r.Question[0]
	if q.Qclass != dns.ClassINET {
		SendError(w, r, dns.RcodeRefused)
		return
	}
	log.Printf("Received query %s from %s", q.String(), w.RemoteAddr().String())
	qval := s.ExtractName(q)
	switch q.Qtype {
	case dns.TypeA:
		if qval == "" {
			SendError(w, r, dns.RcodeRefused)
			return
		}
		s.ServeDNSA(w, r, qval)
	case dns.TypeAAAA:
		if qval == "" {
			SendError(w, r, dns.RcodeRefused)
			return
		}
		s.ServeDNSAAAA(w, r, qval)
	// TODO: support PTR
	default:
		SendError(w, r, dns.RcodeNameError)
		return
	}
}

func (s *DNSServer) ExtractName(q dns.Question) string {
	name := dns.CanonicalName(q.Name)
	if s.domain == "" {
		// For now we just grab the first term
		pieces := dns.SplitDomainName(name)
		if pieces == nil || len(pieces) == 0 {
			return ""
		}
		return pieces[0]
	}
	if !dns.IsSubDomain(s.domain, name) {
		return ""
	}
	// Return the right most piece *not* in s.domain
	labels := dns.CountLabel(s.domain)
	pieces := dns.SplitDomainName(name)
	if len(pieces) <= labels {
		return ""
	}
	return pieces[len(pieces)-labels-1]
}

func (s *DNSServer) ServeDNSA(w dns.ResponseWriter, r *dns.Msg, qval string) {
	log.Printf("Generating A response for %s", qval)
	m := new(dns.Msg)
	m.SetReply(r)
	rr := &dns.A{
		Hdr: dns.RR_Header{
			Name:   r.Question[0].Name,
			Rrtype: r.Question[0].Qtype,
			Class:  r.Question[0].Qclass,
			Ttl:    DNS_TTL,
		},
	}
	m.Answer = append(m.Answer, rr)
	if qval == REFLECT_DNS {
		ip := GetIPFromAddr(w.RemoteAddr()).To4()
		if ip == nil {
			SendError(w, r, dns.RcodeNameError)
			return
		}
		rr.A = ip
		w.WriteMsg(m)
		return
	}
	// We support two formats:
	// hex: 01020304 -> 1.2.3.4
	// str: 1-2-3-4 -> 1.2.3.4
	if len(qval) == 8 {
		if bv, err := hex.DecodeString(qval); err == nil {
			rr.A = net.IP(bv)
			log.Printf("%v -> %v", qval, rr.A.String())
			w.WriteMsg(m)
			return
		}
	}
	// Now we try the - separator
	ip := net.ParseIP(strings.ReplaceAll(qval, "-", ".")).To4()
	if ip == nil {
		SendError(w, r, dns.RcodeNameError)
		return
	}
	rr.A = ip
	log.Printf("%v -> %v", qval, rr.A.String())
	w.WriteMsg(m)
}

func (s *DNSServer) ServeDNSAAAA(w dns.ResponseWriter, r *dns.Msg, qval string) {
	log.Printf("Generating A response for %s", qval)
	m := new(dns.Msg)
	m.SetReply(r)
	rr := &dns.AAAA{
		Hdr: dns.RR_Header{
			Name:   r.Question[0].Name,
			Rrtype: r.Question[0].Qtype,
			Class:  r.Question[0].Qclass,
			Ttl:    DNS_TTL,
		},
	}
	m.Answer = append(m.Answer, rr)
	if qval == REFLECT_DNS {
		ip := GetIPFromAddr(w.RemoteAddr()).To16()
		if ip == nil {
			SendError(w, r, dns.RcodeNameError)
			return
		}
		rr.AAAA = ip
		w.WriteMsg(m)
		return
	}
	// Supporting 2 formats
	// full hex: 32 chars
	// - instead of :
	if len(qval) == 32 {
		if bv, err := hex.DecodeString(qval); err == nil {
			rr.AAAA = net.IP(bv)
			log.Printf("%v -> %v", qval, rr.AAAA.String())
			w.WriteMsg(m)
			return
		}
	}
	ip := net.ParseIP(strings.ReplaceAll(qval, "-", ":")).To16()
	if ip == nil {
		SendError(w, r, dns.RcodeNameError)
		return
	}
	rr.AAAA = ip
	log.Printf("%v -> %v", qval, rr.AAAA.String())
	w.WriteMsg(m)
}

func WithUDPServer(s *DNSServer) error {
	s.withUdp = true
	return nil
}

func WithTCPServer(s *DNSServer) error {
	s.withTcp = true
	return nil
}

func WithDomain(d string) func(*DNSServer) error {
	return func(s *DNSServer) error {
		s.domain = dns.Fqdn(d)
		return nil
	}
}

func GetIPFromAddr(addr net.Addr) net.IP {
	switch v := addr.(type) {
	case *net.UDPAddr:
		return v.IP
	case *net.TCPAddr:
		return v.IP
	case *net.IPAddr:
		return v.IP
	default:
		log.Printf("slow path -- type of addr: %T", v)
		h, _, err := net.SplitHostPort(addr.String())
		if err != nil {
			log.Printf("Error splitting hostport from %v: %v", addr.String(), err)
			return nil
		}
		return net.ParseIP(h)
	}
}
