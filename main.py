# main.py
from telegram_bot.speckle_projects import get_speckle_projects

projects = get_speckle_projects()
for project in projects:
    print(f"Project ID: {project.id}, Project Name: {project.name}")
