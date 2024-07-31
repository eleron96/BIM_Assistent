# # main.py
# from specklepy.api.client import SpeckleClient
# from specklepy.api.credentials import get_default_account
# from collections import defaultdict
# import requests
# import datetime
#
#
# def get_commit_details(client, stream_id, commit_id):
#     commit = client.commit.get(stream_id, commit_id)
#     return commit
#
#
# def get_commit_comments(stream_id, commit_ids, token):
#     url = "https://speckle.xyz/graphql"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }
#     query = """
#     query ($streamId: String!, $resources: [ResourceIdentifierInput]!) {
#       comments(streamId: $streamId, resources: $resources, limit: 1000) {
#         items {
#           id
#           text {
#             doc
#             attachments {
#               id
#               fileName
#               fileType
#               fileSize
#             }
#           }
#           data
#           author {
#             name
#           }
#           createdAt
#         }
#       }
#     }
#     """
#     variables = {
#         "streamId": stream_id,
#         "resources": [{"resourceType": "commit", "resourceId": commit_id} for
#                       commit_id in commit_ids]
#     }
#     response = requests.post(url, headers=headers,
#                              json={"query": query, "variables": variables})
#     if response.status_code == 200:
#         comments = response.json()["data"]["comments"]["items"]
#         return comments
#     else:
#         print(f"Failed to fetch comments: {response.text}")
#         return []
#
#
# def format_comment(comment):
#     author = comment['author']['name']
#     created_at = comment['createdAt']
#     text = comment['text']['doc']
#     text_content = ' '.join(
#         [content['text'] for paragraph in text['content'] for content in
#          paragraph['content'] if 'text' in content])
#
#     # Форматирование времени и даты
#     datetime_obj = datetime.datetime.fromisoformat(created_at[:-1])
#     formatted_datetime = datetime_obj.strftime("[%H:%M %d/%Y]")
#
#     return f"{formatted_datetime} [{author}] {text_content}"
#
#
# def main():
#     HOST = "https://speckle.xyz/"
#
#     # Create and authenticate the client
#     client = SpeckleClient(host=HOST)
#     account = get_default_account()
#     client.authenticate_with_account(account)
#
#     # Token for authentication
#     token = account.token
#
#     # ID проекта из вашей ссылки
#     stream_id = "43890e489f"
#
#     # Получаем все коммиты для указанного проекта
#     commits = client.commit.list(stream_id)
#
#     # Словарь для хранения последних коммитов для каждой модели
#     latest_commits = defaultdict(lambda: None)
#     branch_names = {}
#
#     # Получаем все ветки для указанного проекта
#     branches = client.branch.list(stream_id)
#     for branch in branches:
#         for commit in branch.commits.items:
#             branch_names[commit.id] = branch.name
#
#     # Фильтруем и находим последние коммиты для каждой модели
#     commit_ids = []
#     for commit in commits:
#         commit_details = get_commit_details(client, stream_id, commit.id)
#         referenced_object = commit_details.referencedObject
#         if referenced_object:
#             # Сравниваем временные метки коммитов и сохраняем последний
#             if latest_commits[
#                 referenced_object] is None or commit_details.createdAt > \
#                     latest_commits[referenced_object].createdAt:
#                 latest_commits[referenced_object] = commit_details
#                 commit_ids.append(commit.id)
#
#     # Получаем комментарии для всех последних коммитов
#     all_comments = get_commit_comments(stream_id, commit_ids, token)
#
#     # Печатаем последние коммиты для каждой модели
#     for model_id, commit in latest_commits.items():
#         branch_name = branch_names.get(commit.id, "Unknown")
#         commit_link = f"{HOST}streams/{stream_id}/commits/{commit.id}"
#
#         print(
#             f"Model ID: {model_id}, Commit ID: {commit.id}, Message: {commit.message}, Created At: {commit.createdAt}, Branch: {branch_name}, Link: {commit_link}")
#         # Печатаем все комментарии с форматированием
#         for comment in all_comments:
#             formatted_comment = format_comment(comment)
#             print(f"  {formatted_comment}")
#
#
# if __name__ == "__main__":
#     main()
