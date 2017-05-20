#!/usr/bin/env python3
# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
import json
# import os
import signal
import sys
import threading
import traceback
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import anticsrf
import api_helper
# import json_helper
import minify

REQUIRE_ANTICSRF_POST = True


class Server(BaseHTTPRequestHandler):
    '''
        Base class for handling HTTP requests -- the core of the server.
    '''

    protocol_version = "HTTP/1.1"

    def enable_dynamic_cors(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     KeyError if the remote end never sent an Origin header.
            Effects:    Sends to the remote end a dynamically generated ACAO
                        header or none at all.

            A trick needed to allow CORS from multiple, but not just any, other
            domain.

            The Access-Control-Allow-Origin header can only have one domain as
            its value, so we test if the remote origin is allowed instead, and
            send it back as the ACAO value.

            If the remote origin isn't allowed, no ACAO header is sent, and
            we assume the client implementation will enforce the same-origin
            policy in that case (it's okay if this assumption falls through).
        '''
        http_origin = self.headers["origin"]
        if http_origin in api_helper.ALLOW_FRONTEND_DOMAINS:
            self.send_header("Access-Control-Allow-Origin", http_origin)

    def write_str(self, data):
        '''
            Arguments:  data (a string or other string-like that can be cast to
                        bytes)
            Returns:    None
            Throws:     TypeError if data cannot be encoded to bytes() with
                        UTF8
            Effects:    Modifies self.wfile by writing bytes there.

            Shorthand for writing a string back to the remote end.
        '''
        self.wfile.write(bytes(data, "utf-8"))

    def write_json(self, obj):
        '''
            Arguments:  obj (a dict)
            Returns:    None
            Throws:     json.dumps throws TypeError if the provided argument
                        is not serialisable to JSON, and anything thrown by
                        self.write_str
            Effects:    any side effects of self.write_str

            Take (probably) a Python dictionary and write it to the remote end
                as JSON.

        '''
        self.write_str(json.dumps(obj))

    def write_json_error(self, err, expl=""):
        '''
            Arguments:  err (an object) and expl (an object)
            Returns:    None
            Throws:     anything thrown by self.write_json
            Effects:    any side effects of self.write_json

            Take an error descriptor (a string, or other JSON-serialisable
                object like a number or another dict) and an optional
                explanation, and write them as a JSON object to the remote end.
        '''

        self.write_json( {"error": err, "explanation": expl} )

    def set_headers(self, resp, headers=(), msg=None, close=True, csop=False):
        '''
            Arguments:  resp (an int), headers (a tuple<tuple<string,
                        string>>), msg (a string), and close (a bool)
            Returns:    None
            Throws:     anything thrown by any method it calls (does not throw
                        its own exceptions)
            Effects:    Sends headers to the remote end, and calls
                        self.end_headers, meaning that no more headers can be
                        sent.

            Sends the appropriate headers given an HTTP response code.
            Also sends any headers specified in the headers argument.
            If `headers` evaluates to False, a "Content-Type: application/json"
                header is sent. Otherwise, the Content-Type is expected to be
                present in `headers`.
            An alternate message can be specified, so that instead of "200 OK",
                "200 Hello" could be sent instead.
            If close is True, its default value, the header "Connection: Close"
                is sent. Otherwise, if close evaluates to False, "Connection:
                keep-alive" is sent. This is not recommended.

            If called with 200 as the first argument, the following headers are
                sent:

            HTTP/1.1 200 OK
            Server: BaseHTTP/0.6 Python/3.5.3
            Date: Fri, 19 May 2017 12:14:12 GMT
            Content-Type: application/json
            Access-Control-Allow-Origin: <client origin or omitted>
            Access-Control-Allow-Methods: HEAD,GET,POST,OPTIONS
            Accept: application/json
            Connection: Close
        '''
        self.send_response(resp, message=msg)

        if not headers:
            self.send_header("Content-Type", "application/json")

        else:
            for h in headers:
                self.send_header(*h)

        if csop:
            self.send_header("Access-Control-Allow-Origin", "*")
        else:
            self.enable_dynamic_cors()

        self.send_header(
            "Access-Control-Allow-Methods",
            "HEAD,GET,POST,OPTIONS"
        )
        self.send_header("Accept", "application/json")

        if close:
            self.send_header("Connection", "Close")
        else:
            self.send_header("Connection", "keep-alive")

        self.end_headers()

    def do_HEAD(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     anything thrown by self.set_headers
            Effects:    any side effects of self.set_headers

            Reply to an HTTP HEAD request, sending the default headers.
        '''
        self.set_headers(200)

    # handle GET, reply unsupported
    def do_GET(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     anything thrown by methods called
            Effects:    any side effects of self.wfile.write

            Reply to an HTTP GET request, probably with 404 or 405.

            As yet undocumented: CSOP, Cirque d' Same Origin Policy
        '''
        pathobj = urllib.parse.urlparse(self.path)
        cpath   = pathobj.path[1:]
        qs      = urllib.parse.parse_qs(pathobj.query)
        is_csop = "url" in qs and qs["url"] and qs["url"][0]

        if cpath == "favicon.ico":
            self.set_headers(200, headers=(["Content-Type", "image/x-icon"],))
            with open(cpath, "rb") as icon:
                self.wfile.write(icon.read())

        elif pathobj.path in ["", "/"] and is_csop:
            self.set_headers(200, csop=True)
            import requests, re  # noqa

            # request URL
            url   = qs["url"][0]
            hasprotocol = re.compile(r"^https?:\/\/.+")
            if not re.match(hasprotocol, url):
                url = "http://" + url

            # request method (defaults to GET)
            # ok methods: delete, get, head, patch, post, put
            # sanitise input to disallow code injection
            okmtd = re.compile(r"^(delete|get|head|patch|post|put)$")
            mtd   = re.match(okmtd, qs.get("method", ["get"])[0])
            if mtd:
                mtd = mtd.string
            else:
                mtd = "get"
            mtd   = eval("requests." + mtd)

            # request headers
            # hdrs    = qs.get("header", [])  # get all the uses of the field
            hdr_obj = {}  # api_helper.parse_encoded_headers(*hdrs)  # decode

            # request body
            body = qs.get("body", [""])[0]  # only first use

            # perform the request
            resp = mtd(url, headers=hdr_obj, data=body)
            self.write_json({
                "url":     resp.url,
                "headers": dict(resp.headers)
            })
            self.wfile.write(bytes([1, 2, 3, 4, 7, 0, 0, 13, 10, 13, 10]))

            self.wfile.write(resp.content)

        else:
            self.set_headers(405)
            self.write_json_error("HTTP GET not fully implemented")

    # handle POST based on JSON content
    def do_POST(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     anything thrown by methods it calls that is not caught
                        (does not throw explicity)
            Effects:    sets headers, and those effects of self.write_str

            Reply to an HTTP POST request.

            Interprets the headers, and request body as UTF-8, and expects the
                body to be parsable as JSON.

            The following HTTP status codes may be returned:
            - 200 (OK): the server understood your request and has processed
                it without errors. The response as JSON follows the headers.

            - 400 (Bad Request): the Content-Type header does not have the
                value "application/json", the request body cannot be decoded as
                JSON, the request JSON is missing a required key ("verb",
                "data", or "time"), or the given "verb" requires a key not
                present in the "data" object.

            - 401 (Unauthorized): the request JSON is missing the "anticsrf"
                top-level key even though the "verb" specified would require
                it, the provided "anticsrf" token was never valid or has
                expired since being issued (either expliictly, or because an
                hour elapsed), or the account specified by "gapi_info" does
                not have permission to perform the requested "verb".

            - 406 (Not Acceptable): the server has processed your request but
                found that the "time" top-level key is from the future (that
                is, has a value greater than or equal to the current time in
                milliseconds since 1 January 1970).

            - 411 (Length Required): the server cannot process your request
                past the request headers because the remote end never specified
                the "Content-Length" header.

            - 500 (Internal Server Error): the server cannot process and/or
                respond to your request because it has encountered an internal
                error and crashed. This is probably due to a bug inherent in
                this source code, and could be reported. However, the bug will
                probably be fixed in less than 24 hours.
        '''
        # pathobj = urllib.parse.urlparse(self.path)
        # print(pathobj)
        lock = threading.Lock()
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
        minmsg  = minify.json_minify(msg_str)

        try:
            message = json.loads(minmsg)
        except json.JSONDecodeError as ex:
            self.set_headers(400)
            self.write_json_error(
                "can't process POST body as JSON",
                expl=traceback.format_exc(1)
            )
            return

        try:
            verb, data, time = (
                message[key] for key in ["verb", "data", "time"]
            )
            if time["conn_init"] > api_helper.millitime():
                raise ValueError

        except KeyError as ex:
            self.set_headers(400)
            self.write_json_error(
                "POST body missing key 'data', 'verb' or 'time'"
            )
            return
        except ValueError:
            self.set_headers(406)
            self.write_json_error(
                "server can't service requests from the future",
                expl="JSON data in POST body has declared a time which is"
                + " later than the current time"
            )
            return

        csrf_token = ""
        if "anticsrf" in message["data"]:
            csrf_token = message["data"]["anticsrf"]

        csrf_required = verb not in ["ping", "gapi_validate"]
        csrf_given    = anticsrf.is_registered(csrf_token)

        csrf_valid = False

        if REQUIRE_ANTICSRF_POST and csrf_required and (csrf_token != ""):
            import re
            self.set_headers(401)

            # client code can check if responseText["error"].split("(")[1]
            # starts with EAGAIN and request another token by making another
            # gapi_validate request
            is_eagain = "(EAGAIN?)" if re.match(
                r"^[0-9a-z]{{}}$".format(anticsrf.ANTICSRF_KEYSIZE),
                csrf_token
            ) else ""
            self.write_json_error(
                "JSON body missing key 'anticsrf' but the server is "
                + "configured to require such a token " + is_eagain,
                expl="send the server a gapi_validate request and you will get"
                + " a valid key"
            )
            print("CSRF token missing")
            return

        elif csrf_required and not csrf_given:
            self.set_headers(401)
            self.write_json_error(
                "JSON body 'data' subkey 'anticsrf' is not registered on the"
                + " server side",
                expl="send the server a gapi_validate request and you will get"
                + " a valid key"
            )
            print("CSRF token junk")
            return

        else:
            csrf_valid = True

        reply = dict()
        code  = 200
        ok    = True

        with lock:
            # should exc_verb throw exceptions?
            try:
                data, ok = self.exc_verb(verb, data)
            except Exception as e:
                self.send_error(
                    500,
                    message=", ".join(traceback.format_exc().split("\n"))
                )

        reply = {
            "response": api_helper.verb_reply(verb),
            "data": data,
            "time": message["time"]
        }

        if csrf_valid and not csrf_required:
            reply["anticsrf"] = csrf_token

        if ok == -1:
            # the headers were (hopefully) already sent
            return
        elif ok is True:
            self.set_headers(code)
        else:
            self.set_headers(ok[0], msg=ok[1])

        reply["time"]["conn_server"] = api_helper.millitime()
        self.write_json(reply)

    def do_OPTIONS(self):
        '''
        Arguments:  none
        Returns:    None
        Throws:     anything thrown by self.set_headers
        Effects:    any side effects of self.set_headers

        Reply to an HTTP OPTIONS request.

        Browsers use the OPTIONS method as a 'preflight check' on
            XMLHttpRequest POST calls, to determine which headers are sent and
            to tell whether making such a request would violate the same-origin
            policy.
        '''
        self.set_headers(
            200,
            headers=(
                (
                    "Access-Control-Allow-Headers",
                    "Content-Type, Access-Control-Allow-Headers, Origin, " +
                    "Content-Length, Date, X-Unix-Epoch, Host, Connection"
                ),
            )
        )

    def exc_verb(self, verbstr, data):
        '''
            Arguments:  verbstr (a string) and data (a dict)
            Returns:    a dict, and a status code (True for 200 OK, or the HTTP
                        error for an error)
            Throws:     no
            Effects:    side effects of functions beginning with "reply_" in
                        api_helper

        '''
        import re
        attrs       = dir(api_helper)
        replyfun_re = re.compile(r"^reply_[a-z_0-9]+$")
        filattrs    = list(filter(
            lambda s: None is not re.match(replyfun_re, s),
            attrs
        ))
        # print(list(filattrs))
        funcs       = (eval("api_helper.{}".format(fn)) for fn in filattrs)
        verbnames   = ("_".join(fn.split("_")[1:]) for fn in filattrs)

        verb_func_dict = dict(zip(verbnames, funcs))
        # print(verb_func_dict)
        return verb_func_dict.get(
            verbstr,
            lambda v:
                self.internal_error("API error: bad verb: {}".format(verbstr))
        )(data)

    def internal_error(self, ctx):
        '''
            Arguments:  ctx (a string; context)
            Returns:    an empty dictionary and the code, -1
            Throws:     anything thrown by self.set_headers or
                        self.write_json_error
            Effects:    any side effects of self.set_headers or
                        self.write_json_error

            Signal an Internal Server Error because something Bad happened.
        '''
        self.set_headers(500, msg=ctx)
        self.write_json_error(ctx)
        return {}, -1


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(server_class=ThreadedHTTPServer, handler_class=Server, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    print("Starting httpd on port {}...".format(port))

    httpd.serve_forever()


def main():
    from sys import argv

    print("Starting up...")

    '''    if not init_json_db():
            print("missing template json files, maybe pull or re-clone master")
            exit(3)
    '''
    '''if len(argv) == 3:
        FRONTEND_DOMAIN = argv[2]'''

    if not REQUIRE_ANTICSRF_POST:
        print(
            "WARNING: Not requiring anti-CSRF tokens in API requests!" +
            " I hope this is a developer instance..."
        )

    print(
        ("Allowing CORS from frontends on " +
            len(api_helper.ALLOW_FRONTEND_DOMAINS) * "{} ")
        .format(*api_helper.ALLOW_FRONTEND_DOMAINS)
    )
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
