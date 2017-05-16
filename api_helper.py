#!/usr/bin/env python3
# from os import path
# import sys
import binascii
import json_helper
import os
import gapi_auth
import time

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
    "known_users.json",    # all users ever (?)
    "limits.json",         # rate limiting and banning
    "elevated_ids.json"    # accounts that can edit the menu
    # ?
]

JSON_DIR = "json"

ANTICSRF_REGISTER = {
    # here's a good vulnerability to leave uncommented ;)
    # "token": 12344478634234
}

ANTICSRF_EXPIRY  = 1000 * 60 * 60  # 1 hour
ANTICSRF_KEYSIZE = 42
# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def inttime():
    return round(time.time())


def millitime():
    return round(1000 * time.time())


def is_elevated_id(email, hd=None):
    idn, dom = email.split("@")
    el_ids   = json_helper.get_elevated_ids()
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


def anticsrf_register_tok():
    global ANTICSRF_REGISTER
    anticsrf_clean_expired()  # clean at every opportunity
    tok = binascii.hexlify(os.urandom(ANTICSRF_KEYSIZE)).decode("ascii")
    ANTICSRF_REGISTER[tok] = millitime() + ANTICSRF_EXPIRY  # tokens expire
    return tok


# deliberately and prematurely expire a token
def anticsrf_expire_1_tok(tok):
    global ANTICSRF_REGISTER
    del ANTICSRF_REGISTER[tok]
    # also check for other expired tokens
    return 1 + anticsrf_clean_expired()


def anticsrf_clean_expired():
    global ANTICSRF_REGISTER
    ol = len(ANTICSRF_REGISTER)
    ANTICSRF_REGISTER = dict(filter(
        lambda o: o[1] > millitime(),
        ANTICSRF_REGISTER
    ))
    return abs(len(ANTICSRF_REGISTER) - ol)


def anticsrf_is_registered(tok):
    anticsrf_clean_expired()  # do this first to prevent replays
    return tok in ANTICSRF_REGISTER and ANTICSRF_REGISTER[tok] > millitime()

# following methods take one argument and return an object{} and a
# status value (True for 200 OK or a tuple like (code, message))


def reply_ping(data):
    return {
        "pingback": "ping" in data and data["ping"] == "hello",
    }, True


def reply_gapi_validate(data):
    rval = gapi_auth.validate_gapi_key(data)
    return [
        {
            "anticsrf":  anticsrf_register_tok(),
            "gapi_info": rval[0]
        },
        rval[1]
    ]


def reply_view_orders(data):
    # map needed keys to default values
    # only update missing keys
    data = dict(
        data.items()
        | {
            "age": "new",
            "count": 10,
            "from_end": "head"
        }.items()
    )

    # returns identity function when "from_end" is "head"
    # otherwise returns reversed()
    end_func = (
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


def reply_edit_menu(data):
    if not all(x in data for x in ["gapi_info", "menu_data"]):
        return to_error_json(
            "JSON request to edit the menu missing key"
        ), (400, "POST request to edit the menu requires an absent key")

    gapi_info = gapi_auth._validate_gapi_token(data["gapi_token"])

    if not gapi_info["is_elevated"]:
        return to_error_json(
            "submitting an edit to the menu requires an account with more"
            + " permission"
        ), (401, "an elevated account is required to edit the menu")

    json_helper.register_write("menu", data["menu_data"])

    return {"result": "edit registered in queue"}, True
