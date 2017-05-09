import json
import os


def get_elevated_ids():
    el_ids = dict()
    with open(os.path.join("json", "elevated_ids.json"), "r") as idfile:
        fc = idfile.read()
        # print(fc)
        el_ids = json.loads(fc)

    return el_ids


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
