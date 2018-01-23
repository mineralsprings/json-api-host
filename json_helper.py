#!/usr/bin/env python3
# from api_helper import JSON_FILES, JSON_DIR, JTEMPLATE_DIR
# import shutil
# import os
# import json
# from os import path
# import jsonschema

import coloredlogs
import logging
import time
import transactor.transactor as transactor


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

read_clerk = transactor.read_clerk()
write_clerk = transactor.write_clerk()


def read_server():
    logger.info("database reader thread init")
    while True:
        time.sleep(0)

        def arbiter(x):
            d = (
                x[~read_clerk.fields.request]
                [~read_clerk.fields.STOP_ITERATION],
                x[~read_clerk.fields.request][~read_clerk.fields.nice]
            )
            print(*d)
            return d, 200
        res = read_clerk.do_serve_request(spin=True, func=arbiter)
        if res[0] and "STOPITER" == res[0][0]:
            break

        # etc
        if not read_clerk.have_waiting()[0]:
            time.sleep(0)
        else:
            logger.debug("serving another read request")
    logger.critical("goodbye, reader")


def write_server():
    logger.info("database writer thread init")
    while True:
        time.sleep(0)

        def arbiter(x):
            d = (
                x[~read_clerk.fields.request]
                [~read_clerk.fields.STOP_ITERATION],
                x[~read_clerk.fields.request][~read_clerk.fields.nice]
            )
            print(*d)
            return d, 200
        res = write_clerk.do_serve_request(spin=True, func=arbiter)
        if res[0] and "STOPITER" == res[0][0]:
            break

        # etc
        if not write_clerk.have_waiting()[0]:
            time.sleep(0)
        else:
            logger.debug("serving another write request")
    logger.critical("goodbye, writer")


def kill_all_threads():
    req = {
        ~read_clerk.fields.uuid: transactor.random_key(10),
        # low priority causes other requests to finish first
        # unfortunately it means that it may never stop if we never run out of
        # higher priorities
        # but using an urgent priority or a different sorting strategy risks
        # not completing some requests
        ~read_clerk.fields.nice: transactor.priority.normal,
        ~read_clerk.fields.default_get: "",
        ~read_clerk.fields.STOP_ITERATION: "STOPITER"  # noqa
    }
    for c in [read_clerk, write_clerk]:
        time.sleep(0)
        c.impl_register_request(req)


# when a file gets too large to ask python to reasonably open,
# it should be moved to a new file called filename-<DATE_MOVED>.json.old

def test_client():
    import random
    keys = ()
    for i in range(3):
        keys += transactor.random_key(10),
        nice = random.choice(list(transactor.priority))
        read_clerk.register_read({
            ~read_clerk.fields.uuid: keys[i],
            ~read_clerk.fields.nice: nice,
            ~read_clerk.fields.default_get: "users",
            ~read_clerk.fields.STOP_ITERATION: "continue"  # noqa
        })
        time.sleep(0)
    time.sleep(.5)
    # come back later
    for key in keys:
        logger.debug(read_clerk.get_response(key), "\t", read_clerk.get_status(key))


coloredlogs.install(level="NOTSET", fmt="%(name)s[%(process)d] %(levelname)s %(message)s")
logger = logging.getLogger("jsondb")


# def get_elevated_ids():
#     return load_json_db("elevated_ids")
#
#
# def sort_array_by_id(array, sid="sort_id"):
#     return sorted(array, key=sid)
#
#
# def write_out_templates():
#     for fname, obj in default_objs:
#         apath = path.join(JSON_DIR, fname + ".json")
#         if not path.exist(apath):
#             with open(apath, "w+") as of:
#                 json.dump(obj, of)
#
#
# def validate_json_dir():
#     for name in default_objs.keys():
#         with open(
#                 path.join("schemas/autogen", name + ".schema.json"),
#                 "r"
#         ) as fscma:
#             with open(
#                 path.join(JSON_DIR, name + ".json"),
#                 "r"
#             ) as fjson:
#                     scma, vjson = (
#                         json.load(fscma),
#                         json.load(fjson)
#                     )
#                     jsonschema.validate(vjson, scma)
#     print("All JSON and schemas OK, hooray!")
#
#
# def load_json_db(name):
#     with open(path.join("json", name) + ".json", "r") as jfile:
#         return json.load(jfile)
#     # with open(filename, "r") as jfile:
#     #     obj = minify.json_minify(jfile.read())
#     # print(obj)
#     # return json.loads(obj)
#
#
# if __name__ == '__main__':
# write_out_templates()
# test_client()
