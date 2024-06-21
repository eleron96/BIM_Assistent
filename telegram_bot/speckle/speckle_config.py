# config.py
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config

stream_id = select_speckle_stream()
print(f"Used STREAM_ID: {stream_id}")

# Extracting configuration data from environment variables or .env file
HOST = config('HOST')
# STREAM_ID = config('STREAM_ID') # Retrieved manually from .env
STREAM_ID = stream_id

# Create and authenticate the client
client = SpeckleClient(host=HOST)
account = get_default_account()
client.authenticate_with_account(account)
