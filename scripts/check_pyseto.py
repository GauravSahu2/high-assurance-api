import pyseto
from pyseto import Key
import json
import os

with open("keys/paseto/paseto_private.pem", "rb") as f:
    priv = Key.new(version=4, purpose="public", key=f.read())
with open("keys/paseto/paseto_public.pem", "rb") as f:
    pub = Key.new(version=4, purpose="public", key=f.read())

payload = {"sub": "user1", "exp": 1234567890}
token = pyseto.encode(priv, payload)
print(f"Token: {token.decode()}")

decoded = pyseto.decode(pub, token)
print(f"Payload type: {type(decoded.payload)}")
print(f"Payload: {decoded.payload}")
