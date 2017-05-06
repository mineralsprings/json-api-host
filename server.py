# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import json
import cgi
import shutil

JSON_FILES = [
    "menu.json",          # choosable menu entries
    "orders.json",        # every order ever placed
    "known_users.json"    # all visitors ever (?)
    "limits.json",        # rate limiting and banning
    "editors.json"        # google user ids who can edit the menu
    "server_config.json"  # possibly unused, misc server config
    # ?
]

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def validate_gapi_token(token, clid):
    from oauth2client import client, crypt

    # (Receive token by HTTPS POST)

    try:
        idinfo = client.verify_id_token(token, CLIENT_ID)

        # Or, if multiple clients access the backend server:
        # idinfo = client.verify_id_token(token, None)
        # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
        #    raise crypt.AppIdentityError("Unrecognized client.")

        if idinfo['iss'] not in [
            'accounts.google.com', 'https://accounts.google.com'
        ]:
            raise crypt.AppIdentityError("Wrong issuer.")

        # If auth request is from a G Suite domain:
        # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
        #    raise crypt.AppIdentityError("Wrong hosted domain.")
    except crypt.AppIdentityError:
        pass

    return idinfo


def get_frontend_domain():
    return "https://mineralsprings.github.io"  # temp


class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", get_frontend_domain())
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    # GET sends back a Hello world message
    def do_GET(self):
        self._set_headers()
        self.wfile.write(json.dumps({"hello": "world", "received": "ok"}))

    # POST echoes the message adding a JSON field
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader("content-type"))

        # refuse to receive non-json content
        if ctype != "application/json":
            self.send_response(405)
            self.end_headers()
            self.wfile.write("{'error': 'can\'t recv() non-JSON'}")
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers.getheader("content-length"))
        message = json.loads(self.rfile.read(length))

        if "gapi_key" in message:
            client_id = validate_gapi_token(
                message["gapi_key"],
                message["client_id"]
            )

        # add a property to the object, just to mess with data
        message["received"] = "ok"

        # send the message back
        self._set_headers()
        self.wfile.write(json.dumps(message))


def run(server_class=HTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print "Starting httpd on port %d..." % port
    httpd.serve_forever()


def init_json_db():
    for f in JSON_FILES:
        if (not os.path.exists(f)) and os.path.exists("template_" + f):
            shutil.copyfile("template_" + f, f)
        else:
            print("no template_" + f + " in the current directory, exiting")
            return False
    return True


if __name__ == "__main__":
    from sys import argv

    if not init_json_db():
        print("missing template json files")
        exit(3)

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
