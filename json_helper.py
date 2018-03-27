#!/usr/bin/env python3
# from api_helper import JSON_FILES, JSON_DIR, JTEMPLATE_DIR
# import shutil
# import os
# import json
from os import path
# import jsonschema
import pickledb
import coloredlogs
import logging
import time
import transactor.transactor as transactor

coloredlogs.install(
    level="NOTSET",
    fmt="%(name)s[%(process)d] %(levelname)s %(message)s"
)
logger = logging.getLogger("jsondb")


JSON_FILES = [
    "menu",           # choosable menu entries
    "orders",         # every order ever placed
    "known_users",    # all visitors ever (?)
    "limits",         # rate limiting and banning
    "elevated_ids"    # accounts that can edit the menu
    # ?
]

JSON_DIR = "json"
JSON_EXT = ".json"

###############################################################################


def _is_stop_iteration(x):
    return x[~read_clerk._field.STOP_ITERATION] == "STOPITER"


class RF():
    def dgetall(req):
        dbname = req[~read_clerk._field.default_get]
        db = pickledb.load(path.join(JSON_DIR, dbname) + JSON_EXT, False)
        return db.dgetall(dbname)


class WF():
    pass


def read_arbiter(x):
    req = x[~read_clerk._field.request]
    if _is_stop_iteration(req):
        return "STOPITER", 500
    fun = RF.__getattribute__(RF, req["action"])
    res = fun(req)
    return res, 200


def write_arbiter(x):
    req = x[~read_clerk._field.request]
    if _is_stop_iteration(req):
        return "STOPITER", 500
    fun = WF.__getattribute__(WF, req["action"])
    res = fun(req)
    return res, 200

###############################################################################


read_clerk = transactor.read_clerk()
write_clerk = transactor.write_clerk()

DB_THREAD_YIELD = .4


# the read server takes an action and gives back some data
def read_server():
    logger.info("database reader thread init")
    while True:
        time.sleep(DB_THREAD_YIELD)

        res = read_clerk.do_serve_request(spin=False, func=read_arbiter)
        if res and "STOPITER" == res[0]: break
        if not read_clerk.have_waiting()[0]: time.sleep(0)
        # else: logger.debug("serving another read request")
    logger.critical("goodbye, reader")


# the write server takes an action and some data and gives only a status
def write_server():
    logger.info("database writer thread init")
    while True:
        time.sleep(DB_THREAD_YIELD)

        res = write_clerk.do_serve_request(spin=False, func=write_arbiter)
        if res and "STOPITER" == res[0]: break
        if not write_clerk.have_waiting()[0]: time.sleep(0)
        # else: logger.debug("serving another write request")
    logger.critical("goodbye, writer")


###############################################################################
# json api follows


def kill_all_threads():
    req = {
        ~read_clerk._field.uuid: transactor.random_key(10),
        # low priority causes other requests to finish first
        # unfortunately it means that it may never stop if we never run out of
        # higher priorities
        # but using an urgent priority or a different sorting strategy risks
        # not completing some requests
        ~read_clerk._field.nice: transactor.priority.normal,
        ~read_clerk._field.default_get: "",
        ~read_clerk._field.STOP_ITERATION: "STOPITER"  # noqa
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
            ~read_clerk._field.uuid: keys[i],
            ~read_clerk._field.nice: nice,
            ~read_clerk._field.default_get: "users",
            ~read_clerk._field.STOP_ITERATION: "continue"  # noqa
        })
        time.sleep(0)
    time.sleep(.5)
    # come back later
    for key in keys:
        print(
            str(read_clerk.get_response(key)) + "\t" +
            str(read_clerk.get_status(key))
        )


def get_elevated_ids():
    uuid = transactor.random_key()
    req = {
        ~transactor.request_clerk._field.uuid: uuid,
        ~transactor.request_clerk._field.nice: transactor.priority.normal,
        ~transactor.request_clerk._field.default_get: "elevated_ids",
        ~transactor.request_clerk._field.STOP_ITERATION: "continue",
        "action": "dgetall"
    }
    read_clerk.register_read(req)
    time.sleep(0)
    status = read_clerk.get_status(uuid, keep=True)
    while status is None:
        time.sleep(0)
        status = read_clerk.get_status(uuid, keep=True)

    return read_clerk.get_response(uuid), read_clerk.get_status(uuid)

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
