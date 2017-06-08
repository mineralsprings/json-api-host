import requests
import google.oauth2.id_token as id_token


class AdjustedRequest(requests.Request):
    pass


def make_adj_req(url):
    return requests.get(url)


def verify_id_token(token, api_key):
    return id_token.verfiy_token(token, make_adj_req, audience=api_key)
