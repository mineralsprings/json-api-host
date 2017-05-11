#!/usr/bin/env python3
import sys
import json
import minify
import os


def get_elevated_ids():
    return load_json_file(os.path.join("json", "elevated_ids.json"))


def is_elevated_id(email, hd=None):
    id, dom = email.split("@")
    el_ids  = get_elevated_ids()
    # print(repr(el_ids["devs"]) + "\n", id, dom)

    return (
        (
            id in el_ids["devs"] and (dom == "gmail.com")
        )
        or (
            (id in el_ids["sau9"] and (dom == "sau9.org"))
            and (hd is not None and hd == "sau9.org")
        )
    )


def load_json_file(filename):
    with open(filename, "r") as jfile:
        obj = minify.json_minify(jfile.read())
    print(obj)
    return json.loads(obj)


def verb2verb_reply(s):
    return s + "_reply"


def string2error_json(s):
    return {"error": repr(s)}

if __name__ == '__main__':
    print(load_json_file(sys.argv[1]))
