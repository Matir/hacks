// Tool to compute DHCP 121 options
// Output format is octet separated by colons
// prefixlen:prefix_octets:router IP
// This should match RFC 3442:
// https://datatracker.ietf.org/doc/html/rfc3442
// The format is as used by ISC DHCPD, others may use other formats.

package main

import (
	"flag"
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
)

type RouteInfo struct {
	Subnet *net.IPNet
	Router net.IP
}

func main() {
	decode := flag.String("d", "", "Decode a DHCP Option 121 spec.")
	flag.Parse()

	if *decode != "" {
		if res, err := decodeDHCPOption(*decode); err != nil {
			fmt.Fprintf(os.Stderr, "Failed decoding: %v\n", err)
			os.Exit(1)
		} else {
			for _, r := range res {
				fmt.Printf("%s\n", r)
			}
			os.Exit(0)
		}
	}

	if len(flag.Args()) < 2 {
		flag.Usage()
		os.Exit(1)
	}

	optstring, err := buildOpt(flag.Args())
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(1)
	}

	fmt.Printf("DHCP 121 Option: %s\n", optstring)
}

func buildOpt(args []string) (string, error) {
	inputs := make([]RouteInfo, 0)
	outputs := make([]string, 0)
	for _, arg := range args {
		if strings.Contains(arg, "/") {
			_, ipnet, err := net.ParseCIDR(arg)
			if err != nil {
				return "", fmt.Errorf("Error parsing IP range %v: %w", arg, err)
			}
			inputs = append(inputs, RouteInfo{Subnet: ipnet})
		} else {
			if len(inputs) == 0 {
				return "", fmt.Errorf("Got gateway IP with no networks!")
			}
			rtr := net.ParseIP(arg)
			if rtr == nil {
				return "", fmt.Errorf("Error parsing gateway IP address: %v", arg)
			}
			for _, i := range inputs {
				i.Router = rtr
				outputs = append(outputs, formatDHCP(&i))
			}
			inputs = inputs[:0]
		}
	}
	return strings.Join(outputs, ":"), nil
}

func decodeDHCPOption(optstring string) ([]*RouteInfo, error) {
	octetsStrs := strings.Split(strings.TrimSpace(optstring), ":")
	octets := make([]uint8, len(octetsStrs))
	for i := range octetsStrs {
		if v, err := strconv.ParseUint(octetsStrs[i], 16, 8); err != nil {
			return nil, err
		} else {
			octets[i] = uint8(v)
		}
	}
	results := make([]*RouteInfo, 0)
	for len(octets) > 0 {
		dec, leftover, err := decodeSingle(octets)
		if err != nil {
			return nil, err
		}
		octets = leftover
		results = append(results, dec)
	}
	return results, nil
}

// Decode a single option, then return the leftovers
func decodeSingle(octets []uint8) (*RouteInfo, []uint8, error) {
	if len(octets) == 0 {
		return nil, nil, fmt.Errorf("decodeSingle called with empty set of octets")
	}
	mask, octets := octets[0], octets[1:]
	netlen := int(mask+7) / 8 // need +7 to result in rounding up
	if len(octets) < netlen {
		return nil, nil, fmt.Errorf("insufficienct octets for network portion")
	}
	netoct, octets := octets[:netlen], octets[netlen:]
	netipoct := make([]uint8, 4)
	copy(netipoct, netoct)
	if len(octets) < 4 {
		return nil, nil, fmt.Errorf("insufficient octets for gateway address")
	}
	gateway, octets := octets[:4], octets[4:]
	res := &RouteInfo{
		Subnet: &net.IPNet{
			IP:   net.IP(netipoct),
			Mask: net.CIDRMask(int(mask), 32),
		},
		Router: net.IP(gateway),
	}
	return res, octets, nil
}

func formatDHCP(info *RouteInfo) string {
	size, _ := info.Subnet.Mask.Size()
	res := fmt.Sprintf("%02x:", size)
	for i := range info.Subnet.IP {
		if info.Subnet.Mask[i] == 0 {
			break
		}
		res += fmt.Sprintf("%02x:", info.Subnet.IP[i]&info.Subnet.Mask[i])
	}
	// Right now we only do IPv4 so this is fixed
	// IPv4 is in the right most bytes of IP
	for i := 0; i < 3; i++ {
		res += fmt.Sprintf("%02x:", info.Router[i+12])
	}
	res += fmt.Sprintf("%02x", info.Router[15])
	return res
}

func (ri *RouteInfo) String() string {
	mask, _ := ri.Subnet.Mask.Size()
	return fmt.Sprintf("%s/%d via %s", ri.Subnet.IP, mask, ri.Router)
}
