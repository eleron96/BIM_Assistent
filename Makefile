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
