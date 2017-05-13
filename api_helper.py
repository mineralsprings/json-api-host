#!/usr/bin/env python3
from os import path
import binascii
import json_helper
import os
# import sys
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

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def get_elevated_ids():
    return json_helper.load_json_db("elevated_ids")


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
    return "reply_" + s


def to_error_json(s):
    return {"error": repr(s)}

# following methods take one argument and return a string, an object{} and a
# status value


def reply_ping(data):
    return {
        "pingback": data["ping"] == "hello",
    }, True


def reply_gen_anticsrf(data):
    return {
        "anticsrf": binascii.hexlify(os.urandom(32)).decode("ascii")
    }, True


def reply_gapi_validate(data):
    return gapi_auth.validate_gapi_key(data)


def reply_view_orders(data):
    # map needed keys to default values
    data = dict(
        data.items()
        | {
            "age": "new",
            "count": 10,
            "from_end": "head"
        }.items()
    )

    end_func    = (
        lambda x: x
        if data["from_end"] == "head"
        else lambda x: list(reversed(x))
    )
    num    = int(float(data["count"]))  # noqa to allow number passed as string or float or int
    age    = "cur_orders" if data["age"] == "new" else "old_orders"
    orders = json_helper.load_json_db("orders")

    return end_func(orders[age])[:num], True


def reply_view_menu(data):
    return json_helper.load_json_db("menu"), True


def reply_get_user_limits(data):
    limits = json_helper.load_json_db("limits")
    # user   = None
    # find   = data["gapi_info"]
    for uobj in limits:
        pass
