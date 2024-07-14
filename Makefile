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
# Переменные
SERVER_USER=root
SERVER_IP=194.35.119.49
ARCHIVE=telegram_bot_files.tar.gz
REMOTE_DIR=/root
DOCKER_IMAGE=telegram_bot:latest
CONTAINER_NAME=telegram_bot_container

.PHONY: deploy_all package copy deploy clean deploy-script

# Основная цель
deploy_all: package copy deploy

# Запаковка файлов
package:
	@echo "Packaging files..."
	tar czvf $(ARCHIVE) Dockerfile bot.py main.py pyproject.toml poetry.lock telegram_bot .env

# Копирование архива на удаленный сервер
copy:
	@echo "Copying archive to remote server..."
	scp $(ARCHIVE) $(SERVER_USER)@$(SERVER_IP):$(REMOTE_DIR)/

# Развертывание на удаленном сервере
deploy: deploy-script
	@echo "Deploying on remote server..."
	ssh $(SERVER_USER)@$(SERVER_IP) 'bash -s' < deploy.sh

# Создание скрипта развертывания на удаленном сервере
deploy-script:
	@echo "Creating deploy script..."
	@echo 'cd $(REMOTE_DIR)' > deploy.sh
	@echo 'tar xzvf $(ARCHIVE)' >> deploy.sh
	@echo 'docker build -t $(DOCKER_IMAGE) .' >> deploy.sh
	@echo 'docker stop $(CONTAINER_NAME) || true' >> deploy.sh
	@echo 'docker rm $(CONTAINER_NAME) || true' >> deploy.sh
	@echo 'docker run --name $(CONTAINER_NAME) -d --restart always $(DOCKER_IMAGE)' >> deploy.sh

# Очистка
clean:
	@echo "Cleaning up..."
	rm -f $(ARCHIVE) deploy.sh

