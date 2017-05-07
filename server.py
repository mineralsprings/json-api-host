#!/usr/bin/env python3
# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
from http.server import BaseHTTPRequestHandler, HTTPServer
from oauth2client import client, crypt
from socketserver import ThreadingMixIn
import socketserver
import json
import cgi
import shutil
import os

FRONTEND_DOMAIN = ""

JSON_FILES = [
    "menu.json",          # choosable menu entries
    "orders.json",        # every order ever placed
    "known_users.json",    # all visitors ever (?)
    "limits.json",        # rate limiting and banning
    "editors.json",        # google user ids who can edit the menu
    "server_config.json"  # possibly unused, misc server config
    # ?
]

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def validate_gapi_token(token, clid):

    idinfo = client.verify_id_token(token, CLIENT_ID)

    # Or, if multiple clients access the backend server:
    # idinfo = client.verify_id_token(token, None)
    # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
    #    raise crypt.AppIdentityError("Unrecognized client.")

    if idinfo['iss'] not in [
        'accounts.google.com', 'https://accounts.google.com'
    ]:
        raise crypt.AppIdentityError("wrong-issuer")

    # If auth request is from a G Suite domain:
    # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
    #    raise crypt.AppIdentityError("Wrong hosted domain.")

    return idinfo


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class Server(BaseHTTPRequestHandler):

    def write_out(self, data):
        self.wfile.write(bytes(data, "utf-8"))

    def _set_headers(self, resp):
        self.send_response(resp)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", FRONTEND_DOMAIN)
        # self.send_header("Access-Control-Allow-Methods", "")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers(200)

    # handle GET, reply unsupported
    def do_GET(self):
        self._set_headers(405)
        self.write_out("{'error': 'HTTP GET unsupported for now'}")

    # handle POST based on JSON content
    def do_POST(self):
        ctype = self.headers["content-type"]

        # refuse to receive non-json content
        if ctype != "application/json":
            self._set_headers(405)
            self.write_out(
                "{'error': 'server doesn't process non-JSON in POST requests'}"
            )
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers.get("Content-Length"))
        msg_bytes = self.rfile.read(length)
        msg_str = str(msg_bytes, "utf-8")
        # print("message:", msg_str)
        message = json.loads(msg_str)

        reply = dict()
        code  = 200

        if ("ping" in message) and (message["ping"] == "hello"):
            reply["pingback"] = "ok"

        elif ("gapi_key" in message) and ("client_id" in message):
            client_id = 0
            try:
                client_id = validate_gapi_token(
                    message["gapi_key"],
                    message["client_id"]
                )
            except crypt.AppIdentityError as ex:
                pass  # ???

        # send the message back
        self._set_headers(code)
        self.write_out(json.dumps(reply))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Access-Control-Allow-Headers"
        )
        self.send_header("Access-Control-Allow-Origin", FRONTEND_DOMAIN)
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()


def init_json_db():
    # look for all the files
    for f in JSON_FILES:
        # if one doesn't exist, we need its template
        if (not os.path.exists(f)) and os.path.exists("template_" + f):
            shutil.copyfile("template_" + f, f)
        elif (not os.path.exists(f)) and (not os.path.exists("template_" + f)):
            print("no template_" + f + " in the current directory, exiting")
            return False

    return True


if __name__ == "__main__":
    from sys import argv

    if not init_json_db():
        print("missing template json files, maybe pull or re-clone master")
        exit(3)

    FRONTEND_DOMAIN = "https://mineralsprings.github.io"

    if len(argv) == 3:
        FRONTEND_DOMAIN = argv[2]

    print("Allowing CORS from frontend on {}".format(FRONTEND_DOMAIN))
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
