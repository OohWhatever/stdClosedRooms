import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string

# Файл для хранения индексов
INDEX_FILE = 'channel_indexes.json'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Хранилище для индексов каналов и ролей
channel_index_map = {}

# Название текстового канала для логирования
INDEX_LOG_CHANNEL_NAME = 'index-log'


# Функция для загрузки индексов из файла
def load_indexes():
    global channel_index_map
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r') as f:
                channel_index_map = json.load(f)
                print(f"Загружено {len(channel_index_map)} индексов из {INDEX_FILE}")
        except json.JSONDecodeError:
            print(f"Ошибка чтения файла {INDEX_FILE}. Проверьте его формат.")
    else:
        print(f"Файл {INDEX_FILE} не найден, создаем новый при сохранении.")


# Функция для сохранения индексов в файл
def save_indexes():
    try:
        with open(INDEX_FILE, 'w') as f:
            json.dump(channel_index_map, f, indent=4)
        print(f"Индексы сохранены в {INDEX_FILE}")
    except IOError:
        print(f"Ошибка сохранения файла {INDEX_FILE}. Проверьте права доступа.")


# Функция для генерации уникального случайного индекса из букв и цифр
def generate_unique_index(length=10):
    characters = string.ascii_letters + string.digits  # Буквы и цифры
    while True:
        index = ''.join(random.choices(characters, k=length))
        if index not in channel_index_map:
            return index


# Событие при готовности бота
@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')
    load_indexes()  # Загружаем индексы из файла
    await bot.tree.sync()  # Синхронизация команд слаши

    # Проверяем, существует ли канал для логирования индексов, если нет — создаем его
    guild = bot.guilds[0]  # Получаем первый сервер, на котором бот запущен (для простоты)
    existing_channel = discord.utils.get(guild.text_channels, name=INDEX_LOG_CHANNEL_NAME)
    if not existing_channel:
        try:
            await guild.create_text_channel(INDEX_LOG_CHANNEL_NAME)
            print(f"Создан канал для логов: {INDEX_LOG_CHANNEL_NAME}")
        except discord.DiscordException as e:
            print(f"Ошибка создания канала для логов: {str(e)}")


# Команда для администратора /setindex (генерация случайного индекса из букв и цифр)
@bot.tree.command(name="setindex", description="Установить случайный индекс для канала")
@app_commands.checks.has_permissions(administrator=True)  # Только для администраторов
async def setindex(interaction: discord.Interaction):
    channel = interaction.channel
    role_name = f"access-{channel.name}"  # Уникальное имя роли на основе имени канала

    # Генерация случайного индекса
    index = generate_unique_index()

    try:
        # Создаем роль
        role = await interaction.guild.create_role(name=role_name)

        # Настраиваем доступ к каналу для этой роли
        await channel.set_permissions(role, read_messages=True, send_messages=True)

        # Сохраняем индекс и канал в локальный словарь
        channel_index_map[index] = {"channel_id": channel.id, "role_id": role.id}

        # Сохраняем индексы в файл
        save_indexes()

        # Получаем канал для логов индексов
        log_channel = discord.utils.get(interaction.guild.text_channels, name=INDEX_LOG_CHANNEL_NAME)

        if log_channel:
            # Записываем информацию об индексе, роли и канале в лог-канал
            await log_channel.send(
                f"Индекс {index} присвоен каналу {channel.mention}. Роль {role.mention} создана."
            )

        await interaction.response.send_message(f"Индекс {index} присвоен каналу {channel.name}. Роль {role_name} создана.", ephemeral=True)

    except discord.DiscordException as e:
        await interaction.response.send_message(f"Произошла ошибка: {str(e)}", ephemeral=True)


# Команда для участника /join
@bot.tree.command(name="join", description="Получить доступ к каналу по индексу")
async def join(interaction: discord.Interaction, index: str):
    user = interaction.user

    # Проверяем, существует ли такой индекс
    if index not in channel_index_map:
        await interaction.response.send_message("Неправильный индекс!", ephemeral=True)
        return

    try:
        # Получаем роль, связанную с индексом
        role_data = channel_index_map[index]
        role = interaction.guild.get_role(role_data["role_id"])

        # Добавляем роль пользователю
        await user.add_roles(role)
        await interaction.response.send_message(f"Доступ к каналу предоставлен! Теперь у вас есть доступ к каналу с индексом {index}.", ephemeral=True)

    except discord.DiscordException as e:
        await interaction.response.send_message(f"Произошла ошибка при добавлении роли: {str(e)}", ephemeral=True)


# Проверка на доступ к /setindex только для определенных ролей
@setindex.error
async def setindex_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("У вас нет прав на выполнение этой команды.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Произошла ошибка: {str(error)}", ephemeral=True)


# Запуск бота
bot.run("TOKEN")
