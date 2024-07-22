# BIM Assistant

Telegram bot for managing BIM projects with Speckle and Toggl integration.

## Features

- **Project Management**: View and manage BIM projects and commits via Speckle.
- **Time Tracking**: Track time and manage deadlines with Toggl.
- **User-Friendly**: Easy interaction through Telegram commands.

## Installation

### Prerequisites

- Docker
- Python 3.8+
- Telegram Bot Token
- Speckle Account

### Steps

1. **Clone the repository**:
    ```bash
    git clone https://github.com/eleron96/BIM_Assistent.git
    cd BIM_Assistent
    ```

2. **Set up environment variables**:
    Create a `.env` file:
    ```env
    BOT_TOKEN=your-telegram-bot-token
    HOST=https://speckle.xyz
    SPECKLE_TOKEN=your-speckle-token
    ```

3. **Build and run with Docker**:
    ```bash
    docker build -t bim_assistant .
    docker run -d --env-file .env bim_assistant
    ```

4. **Run locally with Poetry**:
    ```bash
    poetry install
    poetry run python main.py
    ```

## Usage

### Commands

- **/start**: Initialize the bot.
- **/help**: Display help information.
- **/projects**: List Speckle projects.
- **/toggl_menu**: Access Toggl menu.

### Example

1. **Start the bot**: Send `/start`.
2. **View Projects**: Send `/projects`.
3. **Access Toggl Menu**: Send `/toggl_menu`.

## Project Structure

```
BIM_Assistent/
├── telegram_bot/
│   ├── config.py
│   ├── handlers/
│   ├── speckle/
│   ├── toggl/
├── main.py
├── bot.py
├── Dockerfile
├── Makefile
├── pyproject.toml
├── poetry.lock
```

## License

MIT License

