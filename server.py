#!/usr/bin/env python3
# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
from http.server import BaseHTTPRequestHandler, HTTPServer
from oauth2client import client, crypt
from socketserver import ThreadingMixIn
import signal
import traceback
import sys
import socketserver
import json
import cgi
import shutil
import os
import urllib

API_CLIENT_ID = "502024288218-4h8it97gqlkmc0ttnr9ju3hpke8gcatj" + \
    ".apps.googleusercontent.com"

FRONTEND_DOMAIN = "https://mineralsprings.github.io"

JSON_FILES = [
    "menu.json",          # choosable menu entries
    "orders.json",        # every order ever placed
    "known_users.json",    # all visitors ever (?)
    "limits.json",        # rate limiting and banning
    "editors.json",        # google user ids who can edit the menu
    "server_config.json"  # possibly unused, misc server config
    # ?
]

JSON_DIR = "json/"

JTEMPLATE_DIR = "templates/"

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def validate_gapi_token(token):

    idinfo = client.verify_id_token(token, API_CLIENT_ID)
    # print("idinfo:", idinfo)
    if idinfo['iss'] not in [
        'accounts.google.com', 'https://accounts.google.com'
    ]:
        raise crypt.AppIdentityError("Token has wrong issuer")

    return idinfo
    # Or, if multiple clients access the backend server:
    # idinfo = client.verify_id_token(token, None)
    # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
    #    raise crypt.AppIdentityError("Unrecognized client.")

    # If auth request is from a G Suite domain:
    # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
    #    raise crypt.AppIdentityError("Wrong hosted domain.")


class Server(BaseHTTPRequestHandler):
    "docstring"

    '''def __init__(self, request, client_addr, server):
        super().__init__(request, client_addr, server)
        self.pathobj = urllib.parse.urlparse(self.path)'''

    def write_str(self, data):
        self.wfile.write(bytes(data, "utf-8"))

    def set_headers(self, resp, headers=(), msg=None):
        self.send_response(resp, message=msg)

        if not headers:
            self.send_header("Content-Type", "application/json")

        else:
            for h in headers:
                self.send_header(*h)

        # always send this header
        self.send_header("Access-Control-Allow-Origin", FRONTEND_DOMAIN)
        self.send_header(
            "Access-Control-Allow-Methods",
            "HEAD,GET,POST,OPTIONS"
        )
        self.end_headers()

    def do_HEAD(self):
        self.set_headers(200)

    # handle GET, reply unsupported
    def do_GET(self):
        pathobj = urllib.parse.urlparse(self.path)
        print(pathobj)
        if not os.path.exists(cpath or self.path):  # '/'[1:] -> ''
            self.send_error(404, message="{}: Not found".format(self.path))

        elif cpath == "favicon.ico":
            self.set_headers(
                200,
                headers=(
                    ("Content-Type", "image/x-icon"),
                )
            )
            with open(cpath, "rb") as icon:
                self.wfile.write(icon.read())

        elif cpath == "schema.json":
            self.set_headers(200)
            with open(cpath, "r") as scma:
                self.write_str(scma.read())

        elif cpath in JSON_FILES:
            import urlparse
            qs

        else:
            self.set_headers(405)
            self.write_str("{'error': 'HTTP GET unsupported for now'}")

    # handle POST based on JSON content
    def do_POST(self):
        pathobj = urllib.parse.urlparse(self.path)
        print(pathobj)

        ctype = self.headers["content-type"]

        # refuse to receive non-json content
        if ctype != "application/json":
            self.set_headers(405)
            self.write_str(
                "{'error': 'server doesn't process non-JSON in POST requests'}"
            )
            return

        if "content-length" not in self.headers:
            self.set_headers(411)
            self.write_str(
                "{'error': 'request missing Content-Length header'}"
            )
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers.get("Content-Length"))

        msg_bytes = self.rfile.read(length)

        msg_str = str(msg_bytes, "utf-8")

        message = json.loads(msg_str)

        reply = dict()
        code  = 200
        ok    = True

        if ("ping" in message) and (message["ping"] == "hello"):
            reply["pingback"] = "ok"

        elif ("verb" in message) and (message["verb"] == "gapi_validate"):
            client_info = {}
            try:
                client_info = validate_gapi_token(message["data"]["gapi_key"])
            except crypt.AppIdentityError as ex:
                self.send_error(
                    500,
                    message=str(ex),
                    explain=traceback.format_exc()
                )

            else:
                reply = {
                    "response": "gapi_object",
                    "data": client_info
                }

        if ok:
            self.set_headers(code)

        sreply = json.dumps(reply)

        self.write_str(sreply)

    def do_OPTIONS(self):
        self.set_headers(
            200,
            headers=(
                (
                    "Access-Control-Allow-Headers",
                    "Content-Type, Access-Control-Allow-Headers, " +
                    "Content-Length"
                ),
            )
        )


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def init_json_db():
    templ_pfix = "templates/template_"
    # look for all the files
    for f in JSON_FILES:
        # if one doesn't exist, we need its template
        if (not os.path.exists(JSON_DIR + f)) and \
                os.path.exists(templ_pfix + f):
            shutil.copyfile(templ_pfix + f, JSON_DIR + f)

        elif (not os.path.exists(JSON_DIR + f)) and \
                (not os.path.exists(templ_pfix + f)):
            print("no template_" + f + " in ./templates, exiting")
            return False

    return True


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()


def main():
    from sys import argv
    global FRONTEND_DOMAIN

    print("Starting up...")

    if not init_json_db():
        print("missing template json files, maybe pull or re-clone master")
        exit(3)

    if len(argv) == 3:
        FRONTEND_DOMAIN = argv[2]

    print("Allowing CORS from frontend on {}".format(FRONTEND_DOMAIN))
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()


def sigterm_handler(_signo, _stack_frame):
    print("Shutting down...\n")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sigterm_handler)
    try:
        main()
    except KeyboardInterrupt:
        print("\ncaught CTRL-C, exiting")
