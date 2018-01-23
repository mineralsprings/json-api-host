#!/usr/bin/env python3
# adapted from https://gist.github.com/nitaku/10d0662536f37a087e1b
import coloredlogs
import logging
import json
import signal
import sys
import time
import threading
import traceback
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import anticsrf.anticsrf as anticsrf
import api_helper
import json_helper
import dev_vars

import httplib2shim
httplib2shim.patch()

token_clerk = anticsrf.token_clerk(
    # preset_tokens=( ("ab", 3874563875463487), ),
    keysize=42,
    keyfunc=anticsrf.random_key,
    expire_after= (3278465347856738456834754
                   if dev_vars.DEV_DISABLE_TIMESTAMP_CHECKS
                   else (10 ** 6) * (60 ** 2))
)


# def dprint(*args, **kwargs):
#     return
#     if dev_vars.DEV_DBG:
#         print(*args, **kwargs)


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
            domains.

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
        logger.debug("Response: " + str(data))
        self.wfile.write(bytes(data, "utf-8"))

    def write_json(self, obj):
        '''
            Arguments:  obj (a dict)
            Returns:    None
            Throws:     json.dumps throws TypeError if the provided argument
                        is not serialisable to JSON, and anything thrown by
                        self.write_str
            Effects:    inherited

            Take (probably) a Python dictionary and write it to the remote end
                as JSON.

        '''
        self.write_str(json.dumps(obj, indent=2))

    def write_json_error(self, err, expl=""):
        '''
            Arguments:  err (an object) and expl (an object)
            Returns:    None
            Throws:     inherited
            Effects:    inherited

            Take an error descriptor (a string, or other JSON-serialisable
                object like a number or another dict) and an optional
                explanation, and write them as a JSON object to the remote end.
        '''

        self.write_json( {"error": err, "explanation": expl} )

    def set_headers(self, resp, headers=(), msg=None, close=True, csop=False):
        '''
            Arguments:  resp (an int), headers (a tuple<tuple<string,
                        string>>), msg (a string), close (a bool), csop
                        (a bool)
            Returns:    None
            Throws:     inherited
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
            If csop is True, Access-Control-Allow-Origin is set to *, allowing
                requests from anywhere.

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

        self.send_header("Connection", ["keep-alive", "Close"][close] )

        self.send_header(
            "Access-Control-Allow-Methods",
            "HEAD,GET,POST,OPTIONS"
        )
        self.send_header("Accept", "application/json")

        # force HSTS
        self.send_header("Strict-Transport-Security", "max-age=31536000")

        self.end_headers()

    def do_HEAD(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     inherited
            Effects:    inherited

            Reply to an HTTP HEAD request, sending the default headers.
        '''
        self.set_headers(200)

    # handle GET, reply unsupported
    def do_GET(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     inherited
            Effects:    inherited

            Reply to an HTTP GET request, probably with 404 or 405.

            As yet undocumented: SOP Buster is a workaround for the Same Origin
                Policy
        '''
        pathobj = urllib.parse.urlparse(self.path)
        cpath   = pathobj.path[1:]
        qs      = urllib.parse.parse_qs(pathobj.query)
        is_csop = "url" in qs and qs["url"] and qs["url"][0]

        if cpath == "favicon.ico":
            self.set_headers(200, headers=(["Content-Type", "image/x-icon"],))
            with open(cpath, "rb") as icon:
                self.wfile.write(icon.read())

        elif cpath.split(".")[0] in ["sop-buster", "sop_buster", "sopbuster"]:
            from os.path import join
            self.set_headers(200, csop=True)
            with open(join("util", "sopbuster.js"), "rb") as js:
                self.wfile.write(js.read())

        elif pathobj.path in ["", "/"] and is_csop:
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
            request_mtd = eval("requests." + mtd)

            # request headers
            # hdrs    = qs.get("header", [])  # get all the uses of the field
            hdr_obj = {}  # api_helper.parse_encoded_headers(*hdrs)  # decode

            # request body
            body = qs.get("body", [""])[0]  # only first use

            # perform the request
            resp = request_mtd(url, headers=hdr_obj, data=body)

            self.set_headers(
                200,
                csop=True,
                headers=(
                    ("Content-Type",    resp.headers["content-type"]),
                    ("X-Response-Data",
                        urllib.parse.urlencode(
                            {"url": resp.url, "headers": dict(resp.headers)})
                    ), # noqa leave this
                )
            )

            self.wfile.write(resp.content)

        else:
            self.set_headers(405)
            self.write_json_error("HTTP/1.1 GET NotImplemented")

    # handle POST based on JSON content
    def do_POST(self):
        '''
            Arguments:  none
            Returns:    None
            Throws:     inherited
                        (does not throw explicity)
            Effects:    sets headers, and those effects of self.write_str

            Reply to an HTTP POST request.

            Interprets the headers, and request body as UTF-8, and expects the
                body to be parsable as JSON.

            The following HTTP status codes may be returned:

            - 200 (OK): the server understood your request and has processed
                it without errors. The response as JSON follows the headers.

            - 400 (Bad Request): the server cannot process your request because
                - the Content-Type header does not have the value
                    "application/json",
                - the request body cannot be decoded as JSON,
                - the request JSON is missing a required key ("verb", "data",
                    or "time"), or
                - the given "verb" requires a key not present in the "data"
                    object.

            - 401 (Unauthorized): the server cannot process your request
                because
                - the request JSON is missing the "anticsrf" top-level
                    key even though the "verb" specified would require it,
                - the provided "anticsrf" token was never valid or has expired
                    since being issued (either expliictly, or because an hour
                    elapsed), or
                - the account specified by "gapi_info" does not have permission
                    to perform the requested "verb".

            - 406 (Not Acceptable): the server has processed your request but
                found that the "time" top-level key is from the future (that
                is, has a value greater than or equal to the current time in
                microseconds since 1 January 1970).

            - 411 (Length Required): the server cannot process your request
                past the request headers because the remote end never specified
                the "Content-Length" header.

            - 500 (Internal Server Error): the server cannot process and/or
                respond to your request because it has encountered an internal
                error and crashed. This is probably due to a bug inherent in
                this source code, and could be reported. However, the bug will
                probably be fixed in less than 24 hours.

            - 503 (Service Unavailable): the server is currently handling too
                many other requests, or is misconfigured and cannot process
                requests at all. Try your request again shortly, or, if that
                fails, wait 24 hours for the bug to be fixed.
        '''
        self.lock = threading.Lock()
        # refuse to receive non-json content
        if self.headers["content-type"] != "application/json":
            self.set_headers(400)
            self.write_json_error(
                "server doesn't process non-JSON in POST requests")
            return

        if "content-length" not in self.headers:
            self.send_response_only(411)
            return

        length = int(self.headers["content-length"])

        msg_bytes = self.rfile.read(length)

        msg_str = str(msg_bytes, "utf-8")
        logger.debug("Message: " + str(msg_str))

        # read the message and convert it into a python dictionary
        try:
            message = json.loads(msg_str)
        except json.JSONDecodeError as ex:
            self.set_headers(400)
            self.write_json_error(
                "can't process HTTP/1.1 POST body as JSON",
                expl=traceback.format_exc(1)
            )
            return

        try:
            verb, data, time = (
                message[key] for key in ["verb", "data", "time"]
            )
            if (time["conn_init"] > anticsrf.microtime()
                    and not dev_vars.DEV_DISABLE_TIMESTAMP_CHECKS):
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

        logger.debug("Request: " + str(message))

        csrf_reqd = message["verb"] not in ["ping", "gapi_validate"]
        if csrf_reqd:
            csrf_result = self.csrf_validate(message)
            if not csrf_result:
                return

        reply = dict()
        code  = 200
        ok    = True

        with self.lock:
            # should exc_verb throw exceptions?
            try:
                data, ok = self.exc_verb(verb, data)
            except Exception as e:
                self.set_headers(
                    500,
                    msg=", ".join(traceback.format_exc().split("\n"))
                )

        reply = {
            "response": api_helper.verb_reply(verb),
            "data": data,
            "time": message["time"]
        }

        if csrf_reqd and csrf_result:
            reply["anticsrf"] = message["anticsrf"]

        if ok == -1:
            # the headers were (hopefully) already sent
            return
        elif ok is True:
            self.set_headers(code)
        else:
            self.set_headers(ok[0], msg=ok[1])

        reply["time"]["conn_server"] = anticsrf.microtime()
        self.write_json(reply)

    def do_OPTIONS(self):
        '''
        Arguments:  none
        Returns:    None
        Throws:     inherited
        Effects:    inherited

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

        verbnames   = ("_".join( fn.split("_") [1:] )   for fn in filattrs)
        funcs       = (eval("api_helper.{}".format(fn)) for fn in filattrs)

        verb_func_dict = dict(zip(verbnames, funcs))

        args, kwargs = (None,), {}
        if verbstr == "gapi_validate":  # special case
            args   = (token_clerk,)
            kwargs = {"SPOOFING": dev_vars.DEV_SPOOFING_GAPI_REQS}

        return verb_func_dict.get(
            verbstr,
            lambda v:
                self.internal_error("API error: bad verb: {}".format(verbstr))
        )(data, *args, **kwargs)

    def internal_error(self, ctx):
        '''
            Arguments:  ctx (a string; context)
            Returns:    an empty dictionary and the code, -1
            Throws:     no
            Effects:    inherited

            Signal an Internal Server Error because something Bad happened.
        '''
        self.set_headers(500, msg=ctx)
        self.write_json_error(ctx)
        return {}, -1

    def csrf_validate(self, msg):
        '''
            Arguments:  msg (a dict<string, object>)
            Returns:    False for a junk token or some information about the
                        token for good tokens
            Throws:     no
            Effects:    inherited

            Determine whether an anticsrf token as given by the client is
                valid.
        '''
        errexpl = " ".join(
            """the server is configured to require a valid unique
anti-CSRF token with that kind of request; send a
valid token or get one back after making a valid
gapi_validate request""".split("\n"))

        inverr = "message body key 'anticsrf' invalid; it "

        client_token = "anticsrf" in msg and msg["anticsrf"]

        if client_token:
            # we got a token, need to validate it
            cltok_info = token_clerk.is_valid(client_token)
            if cltok_info["reg"]:
                return cltok_info  # NOTE: EARLY RETURNS HERE

            elif cltok_info["old"]:
                self.set_headers(401)
                self.write_json_error(
                    inverr + "was registered but expired at {}"
                    .format(cltok_info["exp"]),
                    expl=errexpl
                )
            else:
                self.set_headers(401)
                self.write_json_error(
                    inverr + "was never registered",
                    expl=errexpl
                )

        else:
            # didn't get a token, need to report it
            self.set_headers(400)
            self.write_json_error(
                inverr + "is missing but required for verb '{}'"
                .format(msg["verb"]),
                expl=errexpl
            )
        return False


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def run(
    server_class=ThreadedHTTPServer,
    handler_class=Server,
    port=api_helper.LOCAL_PORT
  ):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)

    for f in [
        json_helper.read_server,
        json_helper.write_server,
        # json_helper.test_client
    ]:
        time.sleep(0)
        threading.Thread(target=f).start()

    logger.info("Starting HTTP server on {}...".format(port))

    httpd.serve_forever()


def main():
    from sys import argv

    logger.info("=== STARTING ===")

    if not dev_vars.DEV_REQUIRE_ANTICSRF_POST:
        logger.warning("Not requiring anti-CSRF tokens in API requests!")

    num_frontends = len(api_helper.ALLOW_FRONTEND_DOMAINS)
    logger.info(
        ("DynamiCORS on " + num_frontends * "{} ")
        .format(*api_helper.ALLOW_FRONTEND_DOMAINS)
    )
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()


def sigterm_handler(signo, stack_frame):
    print()
    logger.critical("it's all over")
    json_helper.kill_all_threads()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    coloredlogs.install(level="NOTSET", fmt="%(name)s[%(process)d] %(levelname)s %(message)s")  # noqa
    logger = logging.getLogger("server")
    try:
        main()
    finally:
        logger.critical("=== SHUTTING DOWN ===")
        logger.critical(
            "Dead antiCSRF tokens: {}"
            .format(
                ", ".join(
                    "{tok} ({exp})"
                    .format(**locals())
                    for tok, exp in token_clerk.current_tokens.items()
                )
            )
        )
