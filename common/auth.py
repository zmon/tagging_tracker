import os
from functools import wraps

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response

# This entire module was taken from https://bit.ly/2t8LZVD


def jwt_get_username_from_payload_handler(payload):
    username = payload.get('sub').replace('|', '.')
    authenticate(remote_user=username)
    return username


def make_public_key():
    """
    Gets well known info to generate public key
    :return:
    """
    jwks_response = requests.get("https://" + os.environ["AUTH0_URL"] + "/.well-known/jwks.json")
    jwks = jwks_response.json()

    cert = "-----BEGIN CERTIFICATE-----\n" + jwks["keys"][0]["x5c"][0] + "\n-----END CERTIFICATE-----"
    certificate = load_pem_x509_certificate(cert.encode("utf-8"), default_backend())
    return certificate.public_key()


def get_token_auth_header(request):
    """Obtains the access token from the Authorization Header
    """
    auth = request.META.get("HTTP_AUTHORIZATION", None)
    parts = auth.split()
    token = parts[1]

    return token


def requires_scope(required_scope):
    """Determines if the required scope is present in the access token
    Args:
        required_scope (str): The scope required to access the resource
    """
    def require_scope(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_auth_header(args[0])
            public_key = make_public_key()

            decoded = jwt.decode(token, public_key, audience=os.environ["AUTH0_AUDIENCE"], algorithms=["RS256"])

            if decoded.get("scope"):
                token_scopes = decoded["scope"].split()
                if required_scope in token_scopes:
                    return f(*args, **kwargs)

            return Response(
                {"message": "You do not have access to this resource"}, status=status.HTTP_403_FORBIDDEN
            )
        return decorated
    return require_scope