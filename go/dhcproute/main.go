// Tool to compute DHCP 121 options
// Output format is octet separated by colons
// prefixlen:prefix_octets:router IP

package main

import (
	"fmt"
	"net"
	"os"
)

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintf(os.Stderr, "Usage: %s <subnet> <router>\n", os.Args[0])
		os.Exit(1)
	}
	_, ipnet, err := net.ParseCIDR(os.Args[1])
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing IP range: %v\n", err)
		os.Exit(1)
	}
	rtr := net.ParseIP(os.Args[2])
	if rtr == nil {
		fmt.Fprintf(os.Stderr, "Error parsing gateway IP address.\n")
		os.Exit(1)
	}
	res := formatDHCP(ipnet, rtr)
	fmt.Printf("DHCP 121 Option: %s", res)
}

func formatDHCP(ipnet *net.IPNet, rtr net.IP) string {
	size, _ := ipnet.Mask.Size()
	res := fmt.Sprintf("%02x:", size)
	for i := range ipnet.IP {
		if ipnet.Mask[i] == 0 {
			break
		}
		res += fmt.Sprintf("%02x:", ipnet.IP[i]&ipnet.Mask[i])
	}
	// Right now we only do IPv4 so this is fixed
	// IPv4 is in the right most bytes of IP
	for i := 0; i < 3; i++ {
		res += fmt.Sprintf("%02x:", rtr[i+12])
	}
	res += fmt.Sprintf("%02x", rtr[15])
	return res
}
