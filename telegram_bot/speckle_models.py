from specklepy.api.client import SpeckleClient

def get_project_models_and_commits(client: SpeckleClient, project_id: str):
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
