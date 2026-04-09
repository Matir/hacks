#!/usr/bin/env python
import socket
import sys


class TCPclient():

    def tcp_send(self, server, port, msg, timeout=10):
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        
        try:
            with socket.create_connection((server, port), timeout=timeout) as client:
                client.sendall(msg)
                response = client.recv(4096)
                print(response.decode('utf-8', 'ignore'))
        except socket.timeout:
            print(f"Error: Connection to {server}:{port} timed out.", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == '__main__':
    try:
        server = sys.argv[1]
        port = sys.argv[2]
        msg = sys.argv[3]
        port = int(port, 0)
        client = TCPclient()
        client.tcp_send(server, port, msg)
    except IndexError:
        print('Usage: tcp_client.py <server> <port> <message>')
        sys.exit(1)
