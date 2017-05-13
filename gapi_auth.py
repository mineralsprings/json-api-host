from oauth2client import client, crypt
import api_helper
import time as tm


def _validate_gapi_token(token):

    idinfo = client.verify_id_token(token, api_helper.API_CLIENT_ID)
    now = tm.time()

    # print("idinfo:", idinfo)
    if idinfo["iss"] not in [
        "accounts.google.com", "https://accounts.google.com"
    ]:
        raise crypt.AppIdentityError(
            "Token has wrong issuer: {}"
            .format(idinfo["iss"])
        )

    elif ( idinfo["iat"] >= now ) or ( idinfo["exp"] <= now ):
        raise client.AccessTokenCredentialsError(
            "Token has expired or invalid timestamps: issued-at {} expires {}"
            .format(idinfo["iat"], idinfo["exp"])
        )

    elif idinfo["aud"] != api_helper.API_CLIENT_ID:
        # or idinfo["azd"] != API_CLIENT_ID:
        raise crypt.AppIdentityError("Token has wrong API token id")

    hd = None
    if "hd" in idinfo:
        hd = idinfo["hd"]

    idinfo["is_elevated"] = \
        api_helper.is_elevated_id(idinfo["email"], hd=hd)

    return idinfo
    # Or, if multiple clients access the backend server:
    # idinfo = client.verify_id_token(token, None)
    # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
    #    raise crypt.AppIdentityError("Unrecognized client.")

    # If auth request is from a G Suite domain:
    # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
    #    raise crypt.AppIdentityError("Wrong hosted domain.")


# NOTE: THIS IS AN EXC_VERB FUNCTION
def validate_gapi_key(data):
    from api_helper import error_json
    retval = [None, False]

    try:
        retval = (_validate_gapi_token(data["gapi_key"]), True)

    except client.AccessTokenCredentialsError as e:
        retval[0] = error_json(e)

    except crypt.AppIdentityError as e:
        retval[0] = error_json(e)

    return retval
