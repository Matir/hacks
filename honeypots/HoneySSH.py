import socket
import paramiko
import threading
import logging


class _HoneySSHServer(paramiko.ServerInterface):
  def check_auth_password(self, username, password):
    logging.info('Username: %s\tPassword: %s', username, password)
    return paramiko.AUTH_FAILED


class HoneySSH(object):
  def __init__(self, port=2200):
    self.port = port
    self._lock = threading.Lock()
    self._create_key()
    self._create_socket()
    self._clients = []

  def _create_key(self):
    self._key = paramiko.RSAKey.generate(2048)

  def _create_socket(self):
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._socket.bind(('', self.port))
    self._socket.listen(10)

  def serve_forever(self):
    while True:
      conn, addr = self._socket.accept()
      logging.info('Incoming connection from %s', addr)
      ssh_conn = paramiko.Transport(conn)
      ssh_conn.add_server_key(self._key)
      try:
        ssh_conn.start_server(server=_HoneySSHServer())
      except socket.error:
        continue
      with self._lock:
        self._clients.append(ssh_conn)

  def remove_conn(self, conn):
    with self._lock:
      try:
        self._clients.remove(conn)
      except ValueError:
        logging.warning('Could not find client %s', str(conn))


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  honey = HoneySSH()
  honey.serve_forever()
