#!/usr/bin/env python3
# import urllib
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class Server(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)

    def do_GET(self):
        lock = threading.Lock()

        with lock:
            with open("f", "a") as f:
                f.write(self.path + "\n")

        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()

        lock = threading.Lock()

        length = int(self.headers["content-length"])

        msg_bytes = self.rfile.read(length)

        msg = str(msg_bytes, "utf-8")

        with lock:
            with open("f", "a+") as f:
                f.write(msg + "\n")
            with open("f", "r") as f:
                self.wfile.write(bytes(f.read(20), "utf-8"))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()


if __name__ == "__main__":
    run()
