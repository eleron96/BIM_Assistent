# telegram_bot/speckle/speckle_config.py
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account, Account
from decouple import config
from .speckle_projects import get_speckle_projects

HOST = config('HOST')
SPECKLE_TOKEN = config('SPECKLE_TOKEN')

client = SpeckleClient(host=HOST)

account = Account(token=SPECKLE_TOKEN, serverInfo={'url': HOST})
client.authenticate_with_account(account)

def get_speckle_stream_id(project_name):
    projects = get_speckle_projects(client)
    for project in projects:
        if project.name == project_name:
            return project.id
    return None
