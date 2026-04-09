#!/usr/bin/env python
import socket
import sys


class UDPclient():

    def udp_send(self, server, port, msg, timeout=10):
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(timeout)
                client.sendto(msg, (server, port))
                response, addr = client.recvfrom(4096)
                print(response.decode('utf-8', 'ignore'))
        except socket.timeout:
            print(f"Error: Response from {server}:{port} timed out.", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == '__main__':
	try:
		server = sys.argv[1]
		port = sys.argv[2]
		msg = sys.argv[3]
		port = int(port, 0)
		client = UDPclient()
		client.udp_send(server, port, msg)
	except IndexError:
		print('Usage: udp_client.py <server> <port> <message>')
		sys.exit(1)
