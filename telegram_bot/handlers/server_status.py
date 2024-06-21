import psutil
import platform
import time
from datetime import timedelta
from telegram import Update
from telegram.ext import CallbackContext
import asyncio

async def collect_net_stats(interval=5):
    net_io_1 = psutil.net_io_counters()
    await asyncio.sleep(interval)
    net_io_2 = psutil.net_io_counters()

    sent_bytes = net_io_2.bytes_sent - net_io_1.bytes_sent
    recv_bytes = net_io_2.bytes_recv - net_io_1.bytes_recv

    sent_speed = sent_bytes / interval / 1024  # в KB/s
    recv_speed = recv_bytes / interval / 1024  # в KB/s

    sent_mb = net_io_2.bytes_sent / 1024 / 1024  # в MB
    recv_mb = net_io_2.bytes_recv / 1024 / 1024  # в MB

    return sent_speed, recv_speed, sent_mb, recv_mb

def get_server_status():
    # Получаем имя сервера
    server_name = platform.node()

    # Получаем статус сервера
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime = str(timedelta(seconds=uptime_seconds)).split('.')[0]

    # Получаем загрузку CPU
    cpu_load = psutil.cpu_percent(interval=1)

    # Получаем загрузку RAM
    ram_usage = psutil.virtual_memory().percent

    # Получаем свободное место на диске
    disk_usage = psutil.disk_usage('/')
    free_disk_space = disk_usage.free / 1024 / 1024 / 1024  # в GB

    status = {
        "server_name": server_name,
        "uptime": uptime,
        "cpu_load": cpu_load,
        "ram_usage": ram_usage,
        "free_disk_space": free_disk_space
    }

    return status

async def server_status(update: Update, context: CallbackContext):
    status = get_server_status()
    sent_speed, recv_speed, sent_mb, recv_mb = await collect_net_stats()
    message = (
        f"💻 Сервер: {status['server_name']}\n"
        f"⏱ Аптайм: {status['uptime']}\n"
        f"🔥 CPU: {status['cpu_load']}%\n"
        f"💾 RAM: {status['ram_usage']}%\n"
        f"💽 Свободно на диске: {status['free_disk_space']:.2f} GB\n"
        f"🔼 Средняя отправка: {sent_speed:.2f} KB/s\n"
        f"🔽 Средняя загрузка: {recv_speed:.2f} KB/s\n"
        f"📤 Отправлено: {sent_mb:.2f} MB\n"
        f"📥 Загружено: {recv_mb:.2f} MB"
    )
    await update.message.reply_text(message)
