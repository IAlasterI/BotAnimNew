import discord
import threading
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask, jsonify
import requests
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройки и идентификаторы
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VK_SERVICE_KEY = "74294af874294af874294af876770bbcc07742974294af8130370b6b78bee7f2fe11631"  # Сервисный ключ приложения VK
GROUP_ID = "shikimori"  # Короткое имя или ID сообщества
GUILD_ID = 1294014716091306004  # ID сервера

# Настройка бота Discord
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Хранение ID канала для публикации новостей
news_channel_id = None
auto_posting = False  # Флаг для автоматической публикации
last_post_id = None  # Хранит ID последнего поста

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify(status="Bot is active")

@tasks.loop(minutes=5)
async def uptime_ping():
    pass  # Здесь не требуется, UptimeRobot просто проверит /home периодически

def run_flask():
    app.run(host="0.0.0.0", port=5000)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    uptime_ping.start()
    print("Команды загружены на сервере")

# Команда для установки канала новостей
@bot.tree.command(name="setchannel", description="Установить канал для аниме новостей")
@app_commands.describe(channel="Выберите канал для новостей")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global news_channel_id
    news_channel_id = channel.id
    await interaction.response.send_message(f"Канал для новостей установлен на {channel.mention}")

# Команда проверки API Shikimori
@bot.tree.command(name="check", description="Проверяет подключение к Shikimori API")
async def check(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # Отложенный ответ
    try:
        response = requests.get(
            "https://shikimori.one/api/topics",
            params={"limit": 1},
            headers={"User-Agent": "DiscordBot/1.0"}  # Заголовок User-Agent
        )
        response.raise_for_status()  # Проверка успешности запроса
        await interaction.followup.send("API подключен и работает корректно.")
    except requests.exceptions.HTTPError as e:
        await interaction.followup.send(f"Ошибка при подключении к API Shikimori: {e}")
    except Exception as e:
        await interaction.followup.send(f"Произошла ошибка: {e}")

# Команда для получения последней новости из VK
@bot.tree.command(name="get_vk_news", description="Получить последнюю новость из сообщества VK")
async def get_vk_news(interaction: discord.Interaction):
    global last_post_id
    try:
        # Запрос последних новостей
        response = requests.get(
            "https://api.vk.com/method/wall.get",
            params={
                "access_token": VK_SERVICE_KEY,
                "v": "5.131",
                "domain": GROUP_ID,
                "count": 1  # Получаем последний пост
            }
        )
        data = response.json()

        # Проверка на успешный запрос
        if "response" in data:
            post = data["response"]["items"][0]
            text = post["text"]
            post_url = f"https://vk.com/wall{post['owner_id']}_{post['id']}"
            photo_url = None
            
            # Проверяем наличие вложений
            if "attachments" in post and post["attachments"]:
                for attachment in post["attachments"]:
                    if attachment["type"] == "photo":
                        photo_url = attachment["photo"]["sizes"][-1]["url"]
                        break  # Берем только первую фотографию

            # Отправляем в выбранный канал новостей, если он установлен
            global news_channel_id
            if news_channel_id is not None:
                channel = bot.get_channel(news_channel_id)
                if channel is not None:
                    embed = discord.Embed(title="Последняя новость VK", description=text, url=post_url)
                    if photo_url:  # Добавляем фото, если оно есть
                        embed.set_image(url=photo_url)
                    await channel.send(embed=embed)
                    await interaction.response.send_message("Новость успешно отправлена в канал новостей.", ephemeral=True)
                else:
                    await interaction.response.send_message("Канал новостей не найден.", ephemeral=True)
            else:
                await interaction.response.send_message("Канал для новостей не установлен. Используйте команду /setchannel.", ephemeral=True)
        else:
            await interaction.response.send_message("Не удалось получить данные. Возможно, сообщество ограничило доступ.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Произошла ошибка: {e}", ephemeral=True)

# Команда для получения двух последних новостей из VK
@bot.tree.command(name="newtoo", description="Получить две последние новости из сообщества VK")
async def newtoo(interaction: discord.Interaction):
    global last_post_id
    try:
        # Запрос последних новостей
        response = requests.get(
            "https://api.vk.com/method/wall.get",
            params={
                "access_token": VK_SERVICE_KEY,
                "v": "5.131",
                "domain": GROUP_ID,
                "count": 2  # Получаем последние два поста
            }
        )
        data = response.json()

        # Проверка на успешный запрос
        if "response" in data:
            for post in data["response"]["items"]:
                text = post["text"]
                post_url = f"https://vk.com/wall{post['owner_id']}_{post['id']}"
                photo_url = None
                
                # Проверяем наличие вложений
                if "attachments" in post and post["attachments"]:
                    for attachment in post["attachments"]:
                        if attachment["type"] == "photo":
                            photo_url = attachment["photo"]["sizes"][-1]["url"]
                            break  # Берем только первую фотографию

                # Отправляем в выбранный канал новостей, если он установлен
                global news_channel_id
                if news_channel_id is not None:
                    channel = bot.get_channel(news_channel_id)
                    if channel is not None:
                        embed = discord.Embed(title="Новая новость VK", description=text, url=post_url)
                        if photo_url:  # Добавляем фото, если оно есть
                            embed.set_image(url=photo_url)
                        await channel.send(embed=embed)
                    else:
                        await interaction.response.send_message("Канал новостей не найден.", ephemeral=True)
                else:
                    await interaction.response.send_message("Канал для новостей не установлен. Используйте команду /setchannel.", ephemeral=True)
        else:
            await interaction.response.send_message("Не удалось получить данные. Возможно, сообщество ограничило доступ.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Произошла ошибка: {e}", ephemeral=True)

# Автоматическая публикация новых постов
@tasks.loop(seconds=60)  # Проверяем каждые 60 секунд
async def auto_post():
    global last_post_id
    if news_channel_id and auto_posting:
        response = requests.get(
            "https://api.vk.com/method/wall.get",
            params={
                "access_token": VK_SERVICE_KEY,
                "v": "5.131",
                "domain": GROUP_ID,
                "count": 1  # Получаем последний пост
            }
        )
        data = response.json()
        if "response" in data:
            post = data["response"]["items"][0]
            current_post_id = post["id"]
            if last_post_id != current_post_id:  # Проверяем, изменился ли пост
                last_post_id = current_post_id
                text = post["text"]
                post_url = f"https://vk.com/wall{post['owner_id']}_{post['id']}"
                photo_url = None
                
                # Проверяем наличие вложений
                if "attachments" in post and post["attachments"]:
                    for attachment in post["attachments"]:
                        if attachment["type"] == "photo":
                            photo_url = attachment["photo"]["sizes"][-1]["url"]
                            break  # Берем только первую фотографию

                channel = bot.get_channel(news_channel_id)
                if channel is not None:
                    embed = discord.Embed(title="Новая новость VK", description=text, url=post_url)
                    if photo_url:  # Добавляем фото, если оно есть
                        embed.set_image(url=photo_url)
                    await channel.send(embed=embed)

# Команда для запуска автоматической публикации
@bot.tree.command(name="start", description="Запустить автоматическую публикацию новостей из VK")
async def start(interaction: discord.Interaction):
    global auto_posting
    auto_posting = True
    await interaction.response.defer(ephemeral=True)  # Отложенный ответ
    
    # Отправка последнего поста перед запуском автоматической публикации
    try:
        response = requests.get(
            "https://api.vk.com/method/wall.get",
            params={
                "access_token": VK_SERVICE_KEY,
                "v": "5.131",
                "domain": GROUP_ID,
                "count": 1
            }
        )
        data = response.json()
        
        if "response" in data:
            post = data["response"]["items"][0]
            text = post["text"]
            post_url = f"https://vk.com/wall{post['owner_id']}_{post['id']}"
            photo_url = None
            
            # Проверяем наличие вложений
            if "attachments" in post and post["attachments"]:
                for attachment in post["attachments"]:
                    if attachment["type"] == "photo":
                        photo_url = attachment["photo"]["sizes"][-1]["url"]
                        break  # Берем только первую фотографию

            channel = bot.get_channel(news_channel_id)
            if channel is not None:
                embed = discord.Embed(title="Последняя новость VK", description=text, url=post_url)
                if photo_url:  # Добавляем фото, если оно есть
                    embed.set_image(url=photo_url)
                await channel.send(embed=embed)
                await interaction.followup.send("Запущена автоматическая публикация. Последний пост отправлен.", ephemeral=True)
            else:
                await interaction.followup.send("Канал новостей не найден.", ephemeral=True)
        else:
            await interaction.followup.send("Не удалось получить данные. Возможно, сообщество ограничило доступ.", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"Произошла ошибка: {e}", ephemeral=True)

# Команда для остановки автоматической публикации
@bot.tree.command(name="stop", description="Остановить автоматическую публикацию новостей из VK")
async def stop(interaction: discord.Interaction):
    global auto_posting
    auto_posting = False
    await interaction.response.send_message("Автоматическая публикация остановлена.")

# Запускаем бота
threading.Thread(target=run_flask).start()
bot.run(DISCORD_TOKEN)
