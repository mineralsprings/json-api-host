#!/usr/bin/env python3
# import urllib
from multiprocessing import Process, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer
# from socketserver import ThreadingMixIn


class Server(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)

    def do_GET(self):
        lock = Lock()

        with lock:
            with open("f", "a") as f:
                f.write(self.path + "\n")

        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()

        lock = Lock()

        msg_bytes = self.rfile.read(int(self.headers["content-length"]))

        msg = str(msg_bytes, "utf-8")

        if msg == "trunc":
            with lock:
                with open("f", "w+") as f:
                    f.write("truncated\n")
            # return
        else:
            with lock:
                with open("f", "a+") as f:
                    f.write(msg + "\n")
                with open("f", "r") as f:
                    self.wfile.write(bytes(f.read(20) + "\n", "utf-8"))


class MPMixIn:
    """Mix-in class to handle each request in a new Process."""

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.
        In addition, exception handling is done here.
        """
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = Process(target = self.process_request_thread,
                    args = (request, client_address))

        t.start()


class ThreadedHTTPServer(MPMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()


if __name__ == "__main__":
    run()
