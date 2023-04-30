### Calculate DHCP 121 options
# Formatted as a hex string of repeated values of
# {prefix length}{route prefix}{router}
# route prefix is only as many octets as necessary

import ipaddress
import os
import sys


def decode_and_print(octets):
    decoded = decode(octets)
    for route, router in decoded:
        print('{} via {}'.format(route, router))
    return 0


def decode(octets):
    octets = bytes.fromhex(octets.replace(":", ""))
    routes = []
    while octets:
        prefix_len, octets = octets[0], octets[1:]
        assert(prefix_len >= 0 and prefix_len <= 32)
        route_len = (prefix_len + 7)//8
        route_compact, octets = octets[:route_len], octets[route_len:]
        route_full = route_compact + (b"\x00" * (4-route_len))
        assert(len(route_full) == 4)
        router_bytes, octets = octets[:4], octets[4:]
        subnet = ipaddress.ip_network((route_full, prefix_len))
        router = ipaddress.ip_address(router_bytes)
        routes.append((subnet, router))
    return routes


def encode_and_print(args):
    encoded = encode(args)
    raw = "".join("%02x" % o for o in encode)
    colons = ":".join("%02x" % o for o in encode)
    print("Raw: ".format(raw))
    print("OpnSense/PfSense: ".format(colons))


def encode(args):
    rv = []
    while args:
        route_str, router_str, args = args[0], args[1], args[2:]
        route = ipaddress.ip_network(route_str)
        router = ipaddress.ip_address(router_str)
        prefix_len = route.prefixlen
        route_len = (prefix_len + 7)//8
        res = bytes([prefix_len]) + route.network_address.packed[:route_len]
        res += router.packed
        rv.append(res)
    return b"".join(rv)


def main(argv):
    if len(argv) < 2:
        print('Usage:')
        print('    {}  [encodedstring]'.format(argv[0]))
        print('    {}  [[subnet] [router] ...]'.format(argv[0]))
        os.exit(1)
    if len(argv) == 2:
        return decode_and_print(argv[1])
    return encode_and_print(argv[1:])


if __name__ == '__main__':
    os.exit(main(sys.argv))
