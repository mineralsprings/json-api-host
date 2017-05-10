#!/usr/bin/env python3

from os  import path
from sys import argv

import os

import json
import shutil
import time

IDS_FILE_BASE = path.join("json", "elevated_ids")
IDS_FILE_LOCK = IDS_FILE_BASE +   ".lock"
IDS_FILE_JSON = IDS_FILE_BASE +   ".json"
IDS_FILE_TEMP = IDS_FILE_BASE +   ".temp"

LOCK_LASTS = 5  # time in minutes for which the lock is valid


def get_other_kind(kind):
    return "dev" if kind == "sau9" else "sau9"


def add_id(obj, kind, name):
    if name in obj[kind]:
        raise KeyError(
            "value '{}' exists in kind '{}' "
            "(did you mean to 'del' or 'rm' it?)"
            .format(name, kind)
        )
    obj[kind].append(name)
    return obj


def del_id(obj, kind, name):
    if name not in obj[kind]:
        other = get_other_kind(kind)
        raise KeyError(
            "no such value '{}' in kind '{}' {}"
            .format(
                name,
                kind,
                "(did you mean to 'add' or 'mk' it?)"
                if name not in obj[other]
                else "but it is in kind '{}'".format(other)
            )
        )

    del obj[kind][ obj[kind].index(name) ]
    return obj


def bad_method(m):
    raise KeyError(
        "don't know how to '{}' (expected 'add', 'mk', 'del', or 'rm')"
        .format(m)
    )


def main(method, id_kind, id_name, *junk):
    if id_kind not in ["devs", "sau9"]:
        raise KeyError("ID type '{}' not in 'devs', 'sau9'"
                       .format(id_kind))

    call_func = {
        "add": add_id,
        "mk":  add_id,
        "del": del_id,
        "rm":  del_id,
    }.get(
        method,
        lambda x, y, z: bad_method(method)
    )

    if path.exists(IDS_FILE_LOCK):
        with open(IDS_FILE_LOCK, "r") as old_lock:
            start, expire = old_lock.readline().split("-")

        now = time.time()
        if float(expire) < now:
            print(
                "warning: removing lock file that was valid from {} to {}"
                "because it has expired"
                .format(start, expire)
            )
            os.remove(IDS_FILE_LOCK)

        else:
            raise EnvironmentError(
                "Lock file '{}' exists and has not expired or begins in the"
                " future, kill its process and/or delete it"
                .format(IDS_FILE_LOCK)
            )

    with open(IDS_FILE_LOCK, "w") as lock:
        now = time.time()
        lock.write("{}-{}".format(now, now + (LOCK_LASTS * 60)))

    shutil.copy(IDS_FILE_JSON, IDS_FILE_TEMP)

    # os.chmod(IDS_FILE_TEMP, 0o644)
    # print(oct(os.stat(IDS_FILE_TEMP).st_mode))

    with open(IDS_FILE_TEMP, "r") as temp:
        id_obj = json.load(temp)

    print("starting with", repr(id_obj))

    new_obj = call_func(id_obj, id_kind, id_name)

    print("ending with", repr(new_obj))

    assert(new_obj is not None)

    with open(IDS_FILE_TEMP, "w+") as temp:
        json.dump(new_obj, temp)

    os.remove(IDS_FILE_JSON)
    os.rename(IDS_FILE_TEMP, IDS_FILE_JSON)
    os.remove(IDS_FILE_LOCK)


def cleanup():
    os.remove(IDS_FILE_LOCK)

if __name__ == '__main__':
    if not all(
        path.exists(x) for x in
        ["util", "templates", ".git", "schemas", "server.py"]
    ):
        raise EnvironmentError(
            "Run from wrong directory, try again in project root"
        )

    if len(argv) == 1:
        print(
            "usage: update_elevated_ids.py (sau9 | devs) "
            "(add | mk | del | rm) <ID>"
        )
        exit(1)

    elif len(argv) == 2 and argv[1] == "rmtmp":
        cleanup()
        exit(0)

    try:
        main(* ( argv[1:] ) )
    except (KeyError, AssertionError):
        cleanup()
        raise
