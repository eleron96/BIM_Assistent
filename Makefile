# Имя образа и контейнера
IMAGE_NAME=telegram_bot
CONTAINER_NAME=telegram_bot

# Таргет для сборки образа
build:
	docker build -t $(IMAGE_NAME) .

# Таргет для остановки и удаления старого контейнера
stop:
	-docker stop $(CONTAINER_NAME) || true
	-docker rm $(CONTAINER_NAME) || true

# Таргет для запуска нового контейнера
run: stop build
	docker run -d --name $(CONTAINER_NAME) $(IMAGE_NAME)

# Таргет для полного обновления и запуска контейнера
update: run

.PHONY: build stop run update

# Создание пакета и отправка на сервер
package:
	tar czvf telegram_bot_files.tar.gz Dockerfile bot.py main.py pyproject.toml poetry.lock telegram_bot .env
	scp telegram_bot_files.tar.gz root@194.35.119.49:/root/
