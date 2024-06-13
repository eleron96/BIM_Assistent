# telegram_bot/speckle_commits.py
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config

def get_commit_comments(stream_id, commit_id):
    # Extracting configuration data from environment variables or .env file
    HOST = config('HOST')

    # Create and authenticate the client
    client = SpeckleClient(host=HOST)
    account = get_default_account()
    client.authenticate_with_account(account)

    # Get the commit details, including comments
    commit = client.commit.get(stream_id, commit_id)
    # Access comments from commit if available
    comments = commit.comments if hasattr(commit, 'comments') else []

    return comments
