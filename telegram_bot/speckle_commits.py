# telegram_bot/speckle_commits.py
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config

def get_project_commits(project_id):
    # Extracting configuration data from environment variables or .env file
    HOST = config('HOST')

    # Create and authenticate the client
    client = SpeckleClient(host=HOST)
    account = get_default_account()
    client.authenticate_with_account(account)

    # Get the list of commits for the specified project (stream)
    commits = client.commit.list(project_id)

    return commits
