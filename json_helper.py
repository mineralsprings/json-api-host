#!/usr/bin/env python3
# from api_helper import JSON_FILES, JSON_DIR, JTEMPLATE_DIR
# import shutil
# import os
from os import path
import json
import jsonschema
import minify
import api_helper


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


def write_out_templates():
    for fname, obj in default_objs:
        apath = path.join(api_helper.JSON_DIR, fname + ".json")
        if not path.exist(apath):
            with open(apath, "w+") as of:
                json.dump(obj, of)


def validate_json_dir():
    for name in default_objs.keys():
        with open(path.join("schemas/autogen", name + ".schema.json"), "r") as fscma:
            with open(
                path.join(api_helper.JSON_DIR, name + ".json"),
                "r"
            ) as fjson:
                    scma, vjson = (
                        json.load(fscma),
                        json.load(fjson)
                    )
                    jsonschema.validate(vjson, scma)


def load_json_file(filename):
    with open(filename, "r") as jfile:
        obj = minify.json_minify(jfile.read())
    print(obj)
    return json.loads(obj)


if __name__ == '__main__':
    # write_out_templates()
    validate_json_dir()
