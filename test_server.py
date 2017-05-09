#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import socketserver
import urllib


class Server(BaseHTTPRequestHandler):

    def __init__(self, request, client_addr, server):
        super().__init__(request, client_addr, server)
        self.pathobj = urllib.parse.urlparse(self.path)

    def do_HEAD(self):
        self.send_response(200)

    # handle GET, reply unsupported
    def do_GET(self):
        print(self.pathobj)
        self.send_response(200)
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()

if __name__ == "__main__":
    run()
