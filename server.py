#!/usr/bin/env python3
# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
from http.server import BaseHTTPRequestHandler, HTTPServer
from oauth2client import client, crypt
from socketserver import ThreadingMixIn
import signal
import time
import traceback
import sys
import socketserver
import json
import cgi
import shutil
import os
import urllib
import server_helper

API_CLIENT_ID = "502024288218-4h8it97gqlkmc0ttnr9ju3hpke8gcatj" + \
    ".apps.googleusercontent.com"

FRONTEND_DOMAIN = "https://mineralsprings.github.io"

JSON_FILES = [
    "menu.json",          # choosable menu entries
    "orders.json",        # every order ever placed
    "known_users.json",   # all visitors ever (?)
    "limits.json",        # rate limiting and banning
    "server_config.json",  # possibly unused, misc server config
    "elevated_ids.json"   # accounts that can edit the menu
    # ?
]

JSON_DIR = "json"

JTEMPLATE_DIR = "templates"

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def validate_gapi_token(token):

    idinfo = client.verify_id_token(token, API_CLIENT_ID)
    now = time.time()

    # print("idinfo:", idinfo)
    if idinfo["iss"] not in [
        "accounts.google.com", "https://accounts.google.com"
    ]:
        raise crypt.AppIdentityError(
            "Token has wrong issuer: {}"
            .format(idinfo["iss"])
        )

    elif ( idinfo["iat"] >= now ) or ( idinfo["exp"] <= now ):
        raise client.AccessTokenCredentialsError(
            "Token has expired or invalid timestamps: issued-at {} expires {}"
            .format(idinfo["iat"], idinfo["exp"])
        )

    elif idinfo["aud"] != API_CLIENT_ID:
        raise crypt.AppIdentityError("Token has wrong API token id")

    hd = None
    if "hd" in idinfo:
        hd = idinfo["hd"]

    idinfo["is_elevated"] = \
        server_helper.is_elevated_id(idinfo["email"], hd=hd)

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

    def write_str(self, data):
        self.wfile.write(bytes(data, "utf-8"))

    def write_json(self, obj):
        self.write_str(json.dumps(obj))

    def write_json_error(self, err):
        self.write_json(err)

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
        cpath   = pathobj.path[1:]
        qs      = pathobj.query
        # print(pathobj, "cpath:", cpath)

        if pathobj.path == "/" and qs == "":
            self.set_headers(405)
            self.write_str("{'error': 'HTTP GET not fully implemented'}")

        elif (
            cpath not in JSON_FILES
            and not os.path.exists(cpath)
        ):
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
            if qs == "":
                self.set_headers(200)
                with open(os.path.join("json", cpath), "r") as jf:
                    self.write_str(jf.read())

        else:
            self.send_error(404)

    # handle POST based on JSON content
    def do_POST(self):
        pathobj = urllib.parse.urlparse(self.path)
        # print(pathobj)

        # refuse to receive non-json content
        if self.headers["content-type"] != "application/json":
            self.set_headers(400)
            self.write_json_error(
                "server doesn't process non-JSON in POST requests")
            return

        if "content-length" not in self.headers:
            self.send_response_only(411)
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers["content-length"])

        msg_bytes = self.rfile.read(length)

        msg_str = str(msg_bytes, "utf-8")

        try:
            message = json.loads(msg_str)
        except json.JSONDecodeError as ex:
            self.set_headers(400)
            self.write_json_error(
                "can't process POST body as JSON")
            return

        reply = dict()
        code  = 200
        ok    = True

        if "verb" not in message:
            self.set_headers(400)
            self.write_json_error("message missing key 'verb'")

        elif "data" not in message:
            self.set_headers(400)
            self.write_json_error("message missing key 'data'")

        try:
            response, data, ok = \
                self.exc_verb(message["verb"], message["data"])
        except Exception as ex:
            pass
        else:
            reply = {
                "response": response,
                "data": data
            }

        if ok:
            self.set_headers(code)
        # else the headers were hopefully already sent

        self.write_json(reply)

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

    def exc_verb(self, verbstr, data):
        return {
            "gapi_validate": self.wrap_validate_gapi_key,
            "ping":          self.reply_ping
        }.get(
            verbstr,
            lambda v:
                self.internal_error("API error: bad verb: {}".format(verbstr))
        )(data)

    def internal_error(self, ctx):
        self.set_headers(500, msg=ctx)
        return False

    """ NON-HTTP-METHODS """

    def wrap_validate_gapi_key(self, data):
        try:
            cl_info = validate_gapi_token(data["gapi_key"])
        except client.AccessTokenCredentialsError as e:
            self.set_headers(200)
            return "gapi_validated", {"error": repr(e)}, False
        except crypt.AppIdentityError as e:
            self.set_headers(200)
            return "gapi_validated", {"error": repr(e)}, False
        else:
            return "gapi_validated", cl_info, True

    def reply_ping(self, data):
        return "ping_reply", {
            "pingback": data["ping"] == "hello"
        }, True


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def init_json_db():
    templ_pfix = "templates/template_"
    # look for all the files
    for f in JSON_FILES:
        # if one doesn't exist, we need its template
        if (not os.path.exists(os.path.join(JSON_DIR, f))) and \
                os.path.exists(os.path.join(templ_pfix, f)):
            shutil.copyfile(
                os.path.join(templ_pfix, f),
                os.path.join(JSON_DIR, f)
            )

        elif (not os.path.exists(os.path.join(JSON_DIR, f))) and \
                (not os.path.exists(os.path.join(templ_pfix, f))):
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
