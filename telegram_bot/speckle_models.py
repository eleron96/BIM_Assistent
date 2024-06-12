# telegram_bot/speckle_models.py
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config

def get_project_models_and_commits(project_id):
    # Extracting configuration data from environment variables or .env file
    HOST = config('HOST')

    # Create and authenticate the client
    client = SpeckleClient(host=HOST)
    account = get_default_account()
    client.authenticate_with_account(account)

    # Get the list of branches (models) for the specified project (stream)
    branches = client.branch.list(project_id)

    models = []
    for branch in branches:
        # Get the list of commits for each branch (model)
        commits = client.commit.list(project_id)
        # Filter commits to get the latest commit for the current branch
        latest_commit = next((commit for commit in commits if getattr(commit, 'branchName', '') == branch.name), None)
        models.append({
            "name": branch.name,
            "latest_commit_message": latest_commit.message if latest_commit else "No commits",
            "latest_commit_id": latest_commit.id if latest_commit else None
        })

    return models
