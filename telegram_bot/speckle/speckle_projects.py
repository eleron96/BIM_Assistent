from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config

def get_speckle_projects(client: SpeckleClient = None):
    if client is None:
        # Extracting configuration data from environment variables or .env file
        HOST = config('HOST')

        # Create and authenticate the client
        client = SpeckleClient(host=HOST)
        account = get_default_account()
        client.authenticate_with_account(account)

    # Get the list of streams (projects) available for the account
    streams = client.stream.list()

    return streams
