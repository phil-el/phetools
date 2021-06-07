#
# @file tool_connect.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import socket
import thread
import os
import json
import sys
import urllib.parse



class ToolConnect:
    def __init__(self, server_name, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(('', port))
        except:
            print("could not start listener : socket already in use")
            thread.interrupt_main()
            return

        self.sock.listen(1)
        self.sock.settimeout(None)

        # The other side needs to know the server name where the daemon run to
        # open he connection. We write it after bind() because we want to
        # ensure only one instance of the daemon is running.
        home = os.path.expanduser('~/wikisource/')
        servername_filename = home + server_name + '.server'
        if os.path.exists(servername_filename):
            os.chmod(servername_filename, 0o644)
        fd = open(servername_filename, "w")
        fd.write(socket.gethostname() + ':' + str(port))
        fd.close()
        os.chmod(servername_filename, 0o444)

    def _ill_formed_request(self, conn, data):
        try:
            print("ill formed request", data, file=sys.stderr)
        except:
            pass
        self.send_reply(conn, {'error': 4, 'text': 'Ill formed request'})
        conn.close()

    def wait_request(self):
        request = None
        conn = None
        while not request:
            conn, addr = self.sock.accept()
            data = conn.recv(1024)
            try:
                request = json.loads(data)
            except UnicodeDecodeError:
                self._ill_formed_request(conn, data)
                request = None

            if request:
                for key in request:
                    try:
                        value = urllib.parse.unquote(request[key])
                        request[key] = value
                    except:
                        self._ill_formed_request(conn, data)
                        request = None
                        # Neeed because _ill_formed_request close the conn, so
                        # we break the loop to avoid to call it again.
                        break

        return request, conn

    def send_text_reply(self, conn, data):
        if conn:
            conn.sendall(data)

    def send_reply(self, conn, data):
        if conn:
            data = json.dumps(data)
            conn.sendall(data)

    def close(self):
        if self.sock:
            self.sock.close()


if __name__ == "__main__":
    pass
