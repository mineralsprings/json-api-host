#!/usr/bin/env python3
from os import path
import binascii
import json_helper
import os
import sys
import gapi_auth

API_CLIENT_ID = "502024288218-4h8it97gqlkmc0ttnr9ju3hpke8gcatj" + \
    ".apps.googleusercontent.com"

ALLOW_FRONTEND_DOMAINS = [
    "http://localhost:8080",
    "http://localhost:3000",
    "https://mineralsprings.github.io"
]

JSON_FILES = [
    "menu.json",           # choosable menu entries
    "orders.json",         # every order ever placed
    "known_users.json",    # all visitors ever (?)
    "limits.json",         # rate limiting and banning
    "elevated_ids.json"    # accounts that can edit the menu
    # ?
]

JSON_DIR = "json"

JTEMPLATE_DIR = "templates"


# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old

def get_elevated_ids():
    return json_helper.load_json_file(path.join(JSON_DIR, "elevated_ids.json"))


def is_elevated_id(email, hd=None):
    idn, dom = email.split("@")
    el_ids  = get_elevated_ids()
    # print(repr(el_ids["devs"]) + "\n", id, dom)

    return (
        (
            idn in el_ids["devs"] and (dom == "gmail.com")
        )
        or (
            (idn in el_ids["sau9"] and (dom == "sau9.org"))
            and (hd is not None and hd == "sau9.org")
        )
    )


def verb_reply(s):
    return s + "_reply"


def to_error_json(s):
    return {"error": repr(s)}


def reply_ping(data):
    return verb_reply("ping"), {
        "pingback":       data["ping"] == "hello",
    }, True


def reply_gen_anticsrf(data):
    return verb_reply("gen_anticsrf"), {
        "anticsrf": str(binascii.hexlify(os.urandom(32)))
    }, True


def reply_gapi_validate(data):
    return gapi_auth.validate_gapi_key(data)


if __name__ == '__main__':
    print(json_helper.load_json_file(sys.argv[1]))
