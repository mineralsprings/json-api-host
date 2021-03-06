#!/usr/bin/env python3
# from os import path
# import sys
import gapi_auth
import json_helper
import coloredlogs
import logging

API_CLIENT_ID = "502024288218-4h8it97gqlkmc0ttnr9ju3hpke8gcatj" + \
    ".apps.googleusercontent.com"

LOCAL_PORT = 9000

ALLOW_FRONTEND_DOMAINS = [
    "http://localhost:" + str(LOCAL_PORT),
    "http://localhost:3000",
    "https://mineralsprings.github.io",
    # "https://web-catnipcdn.pagekite.me"
]

coloredlogs.install(
    level="NOTSET",
    fmt="%(name)s[%(process)d] %(levelname)s %(message)s"
)
logger = logging.getLogger("api_helper")


def is_elevated_id(email, hd=None):
    idn, dom = email.split("@")
    el_ids, status = json_helper.all_entires("elevated_ids")
    if status == -1:
        return False

    return (
        (
            idn in el_ids["devs"]
            and (dom == "gmail.com")
        ) or (
            idn in el_ids["sau9"]
            and (dom == "sau9.org")
            and hd == "sau9.org"
        )
    )


def verb_reply(s):
    return "reply_" + s


def to_error_json(s):
    return {"error": repr(s)}


# following methods take one argument and return an object{} and a
# status value (True for 200 OK or a tuple like (code, message))


def reply_ping(data, *args, **kwargs):
    return {
        "pingback": "ping" in data and data["ping"] == "hello",
    }, True


def reply_gapi_validate(data, *args, **kwargs):
    if kwargs["SPOOFING"]:
        rval = "yeah idc what you sent me i'm a dev server", True
    else:
        rval = gapi_auth.validate_gapi_key(data)

    return [
        {
            "anticsrf":  args[0].register_new(),
            "gapi_info": rval[0]
        },
        rval[1]
    ]


def reply_view_orders(data, *args, **kwargs):
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
    num    = int(float(data["count"]))  # noqa to allow number as string or float or int
    age    = "cur_orders" if data["age"] == "new" else "old_orders"
    orders = json_helper.all_entires("orders")

    return end_func(orders[age])[:num], True


def reply_view_menu(data, *args, **kwargs):
    return json_helper.all_entires("menu"), True


def reply_get_user_limits(data, *args, **kwargs):
    limits = json_helper.all_entires("limits")
    # user   = None
    # find   = data["gapi_info"]
    for uobj in limits:
        pass


def reply_edit_menu(data, *args, **kwargs):
    if not all(x in data for x in ["gapi_token", "menu_data"]):
        return to_error_json(
            "JSON request to edit the menu missing key"
        ), (400, "POST request to edit the menu requires an absent key")

    gapi_info = gapi_auth._validate_gapi_token(data["gapi_token"])

    if not gapi_info["is_elevated"]:
        return to_error_json(
            "submitting an edit to the menu requires an account with more"
            + " permission"
        ), (401, "an elevated account is required to edit the menu")

    # TODO: write this
    # json_helper.register_write("menu", data["menu_data"])

    return {"result": "edit registered in queue"}, True


def reply_open_order(data, *args, **kwargs):
    pass


def reply_close_order(data, *args, **kwargs):
    pass
