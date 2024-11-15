from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from decouple import config


def get_speckle_projects(client: SpeckleClient = None, limit: int = 100):
    if client is None:
        HOST = config('HOST')
        client = SpeckleClient(host=HOST)
        account = get_default_account()
        client.authenticate_with_account(account)

    # Получаем все проекты (streams) для аккаунта
    streams = client.stream.list(stream_limit=limit)
    return streams



