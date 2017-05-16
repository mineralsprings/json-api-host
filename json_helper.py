#!/usr/bin/env python3
# from api_helper import JSON_FILES, JSON_DIR, JTEMPLATE_DIR
# import shutil
# import os
from os import path
import json
import jsonschema
# import minify

default_objs = {
    "elevated_ids": {
        "devs": [
            "thebinaryminer"
        ],
        "sau9": [
            "1742119",
            "1858067",
            "d_richardi",
            "v_schrader"
        ]
    },

    "known_users": {
        # empty
    },

    "limits": {

    },

    "menu": {

    },

    "orders": {

    }
}

JSON_FILES = [
    "menu",           # choosable menu entries
    "orders",         # every order ever placed
    "known_users",    # all visitors ever (?)
    "limits",         # rate limiting and banning
    "elevated_ids"    # accounts that can edit the menu
    # ?
]

JSON_DIR = "json"

# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old


def get_elevated_ids():
    return load_json_db(path.join(JSON_DIR, "elevated_ids.json"))


def sort_array_by_id(array, sid="sort_id"):
    return sorted(array, key=sid)


def write_out_templates():
    for fname, obj in default_objs:
        apath = path.join(JSON_DIR, fname + ".json")
        if not path.exist(apath):
            with open(apath, "w+") as of:
                json.dump(obj, of)


def validate_json_dir():
    for name in default_objs.keys():
        with open(
                path.join("schemas/autogen", name + ".schema.json"),
                "r"
        ) as fscma:
            with open(
                path.join(JSON_DIR, name + ".json"),
                "r"
            ) as fjson:
                    scma, vjson = (
                        json.load(fscma),
                        json.load(fjson)
                    )
                    jsonschema.validate(vjson, scma)
    print("All JSON and schemas OK, hooray!")


def load_json_db(filename):
    with open(path.join("json", filename) + ".json", "r") as jfile:
        return json.load(jfile)
    # with open(filename, "r") as jfile:
    #     obj = minify.json_minify(jfile.read())
    # print(obj)
    # return json.loads(obj)


if __name__ == '__main__':
    # write_out_templates()
    validate_json_dir()
