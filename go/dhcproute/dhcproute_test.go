package main

import (
	"net"
	"testing"
)

func TestDHCPRoutes(t *testing.T) {
	testcases := []struct {
		subnet string
		router string
		option string
	}{
		{"192.168.0.0/16", "192.168.20.1", "10:c0:a8:c0:a8:14:01"},
		{"10.0.0.0/8", "172.16.10.1", "08:0a:ac:10:0a:01"},
		{"172.16.0.0/12", "172.16.10.126", "0c:ac:10:ac:10:0a:7e"},
		{"192.168.0.0/16", "172.16.10.126", "10:c0:a8:ac:10:0a:7e"},
	}
	for _, tcase := range testcases {
		_, ipnet, err := net.ParseCIDR(tcase.subnet)
		if err != nil {
			t.Fatalf("Bad test data: %v: %v", tcase.subnet, err)
			return
		}
		rtr := net.ParseIP(tcase.router)
		if rtr == nil {
			t.Fatalf("Bad test data: %v does not parse!", tcase.router)
		}
		result := formatDHCP(&RouteInfo{ipnet, rtr})
		if result != tcase.option {
			t.Errorf("%s->%s, got %s, expected %s", tcase.subnet, tcase.router, result, tcase.option)
		}
	}
}
