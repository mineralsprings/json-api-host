from glob import glob
from os.path import exists, join
from time import sleep

from api_helper import microtime

DIR_LOCKED = "locked"
DIR_JSON   = "json"

JSON_FILES = {
    "elevated_ids": 0,
    "known_users": 0,
    "limits": 0,
    "menu": 0,
    "orders": 0
}


def queue_write(name, data):
    now = microtime()
    if name not in JSON_FILES:
        raise OSError("DB does not exist: {}".format(name))
    fname = join(DIR_LOCKED, str(now) + ".write." + name)
    with open(fname, "w+") as f:
        f.write(data)


def queue_read(name):
    # now = microtime()
    if name not in JSON_FILES:
        raise OSError("DB does not exist: {}".format(name))
    wait_writers(name)
    JSON_FILES[name] += 1
    data = do_read(name)
    JSON_FILES[name] -= 1
    return data


def has_writers(name):
    return len(glob(join(DIR_LOCKED, "*.write." + name))) > 0


def has_readers(name):
    return JSON_FILES[name] > 0


def wait_writers(name):
    while has_writers(name):
        sleep(.5)
    return True


def wait_readers(name):
    pass


def do_write(name):
    pass


def do_read(name):
    pass
