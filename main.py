#-------------------------------------------------------------------------------------------------------------------ИМПОРТЫ
import asyncio
import logging
import re
import os
import random
import json
import sqlite3
import pytz
import yt_dlp
import aiohttp
import zipfile
from aiogram.client.default import DefaultBotProperties
from dates import SPECIAL_EVENTS
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from aiogram.utils.text_decorations import html_decoration as hd
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Для расписания
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.types import LinkPreviewOptions, FSInputFile
from datetime import datetime, timedelta
from aiogram.filters import CommandObject, Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from openai import AsyncOpenAI

#-------------------------------------------------------------------------------------------------------------------ПЕРЕМЕННЫЕ И НАСТРОЙКИ

BOT_TOKEN = "8745666975:AAH8k3HZBgNceAyK_zbV82WuwUSu-uPiFnU"
OPENAI_API_KEY = "sk-VceymhbQITrkT8qoYFshaQ"
BUNGIE_API_KEY = "58ae872eeddb40758274693fd5a48e5c"

BOT_GUIDE = "https://telegra.ph/BaraholkaBot-02-19"
LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814" 

OWNER_ID = 832840031

PENDING_VERIFICATION = {}
USER_STATS = {}
PROCESSED_ALBUMS = []
LAST_MESSAGE_TIME = datetime.now()
AI_COOLDOWN_TIME = datetime.now()
SUMMARY_COOLDOWN_TIME = datetime.now()
CHAT_HISTORY = {}
SILENT_MODE_USERS = []

ADMIN_CHAT_ID = -1003846681143
CHAT_ID = -1003882623791
DEV_CHAT_ID = -1003614362998

#-------------------------------------------------------------------------------------------------------------------СПИСКИ И ФРАЗЫ

UNMUTE_PHRASES = [
    "Био-сканирование завершено. @username снова в строю. <tg-emoji emoji-id='5318818333213075371'>🗣</tg-emoji>",
    "Связь восстановлена. Говори, @username. <tg-emoji emoji-id='5318818333213075371'>🗣</tg-emoji>",
    "Крио-камера разблокирована для @username. <tg-emoji emoji-id='5318818333213075371'>🗣</tg-emoji>"
]

ADMIN_MUTE_PHRASES = [
    "<b>КРИО-СОН.</b> @username заморожен на {time} мин. <tg-emoji emoji-id='5319055531371930585'>🙅‍♂️</tg-emoji>",
    "<b>ОТКАЗ СИСТЕМЫ.</b> Голосовой модуль @username отключен. ({time} мин) <tg-emoji emoji-id='5319055531371930585'>🙅‍♂️</tg-emoji>",
    "<b>НАРУШЕНИЕ ПРОТОКОЛА.</b> @username изолирован от сети. ({time} мин) <tg-emoji emoji-id='5319055531371930585'>🙅‍♂️</tg-emoji>",
    "UESC отключила подачу кислорода для @username на {time} мин. <tg-emoji emoji-id='5319055531371930585'>🙅‍♂️</tg-emoji>"
]

TAPIR_PHRASES = [
    "Тапир? Это не животное, это диагноз твоему провайдеру. Врубай КВН. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Опять Marathon не пускает? Плак-плак. Bungie передают привет твоему айпишнику. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Слышу 'тапир' — вижу человека, который забыл включить КВН. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Ошибка TAPIR... Земля пухом твоему луту. Без КВН ты тут никто. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "У всех всё работает, только у тебя тапир. Может, проблема в прокладке между стулом и монитором? <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Код ошибки: ТЫ ЗАБЫЛ КУПИТЬ НОРМАЛЬНЫЙ КВН. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Тапир пришел за твоим лутом. Смирись и иди гуляй. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Marathon намекает, что ты сегодня не раннер, а ждун. Проверь соединение, гений. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Лови тапира за хвост! А, ой, ты же даже в меню зайти не можешь... <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>",
    "Тапир — это кара за твои грехи. Или просто Роскомнадзор шалит, врубай КВН. <tg-emoji emoji-id='5319185561506816272'>😊</tg-emoji>"
]

MUTE_SHORT_PHRASES = [
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> <b>КРИТИЧЕСКИЙ СБОЙ.</b> Твой чип перегорел, @username.",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> <b>ВЫСТРЕЛ.</b> @username выбывает из забега. (Мут 15 мин)",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> <b>ДЕИНСТАЛЛЯЦИЯ.</b> @username удален из базы данных. (Мут 15 мин)"
]

MUTE_CRITICAL_PHRASES = [
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> КРИТИЧЕСКИЙ УРОН! @username словил хедшот с ульты. Молчишь 30 МИНУТ.",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> Вайп! Ты подвел команду. @username отправляется в мут на 30 МИНУТ.",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> Архитекторы решили тебя уничтожить. @username замучен чате на 30 минут.",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> Громовой удар! Посиди в муте 30 минут, только без паники.",
    "<tg-emoji emoji-id='5463186335948878489'>⚰️</tg-emoji> В твоё лицо снова прилетело. Теперь ты изуродован. (30 мин.)"
]

SAFE_PHRASES = [
    "<tg-emoji emoji-id='5467538555158943525'>💭</tg-emoji> Щелчок... Пусто. MIDA благоволит тебе.",
    "<tg-emoji emoji-id='5467538555158943525'>💭</tg-emoji> Осечка. Твой код еще пригодится.",
    "<tg-emoji emoji-id='5467538555158943525'>💭</tg-emoji> Патронник пуст. Беги дальше, Раннер."
]

KEEP_POSTED_STICKER_ID = "CAACAgIAAxkBAAEQSpppcOtmxGDL9gH882Rg8pZrq5eXVAACXZAAAtfYYEiWmZcGWSTJ5TgE"

REFUND_KEYWORDS = ["рефанд", "refund", "refound", "возврат средств", "вернуть деньги"]

VPN_PHRASES = ["Ты имел ввиду КВН? Измени сообщение, эти 3 буквы запрещены в чате."]

BAD_WORDS = ["лгбт", "цп", "цп", "child porn", "cp", "закладки", "мефедрон", "гашиш", "купить скорость", "чурка", "хохол", "кацап", 
    "москаль", "свинособак", "черномаз", "hohol", 
    "магазин 24/7", "hydra", "kraken", "убейся", "выпей яду", "роскомнадзорнись", "мамку ебал", "зеленский", "либераха", "гейропа", "фашист"] 

BAN_WORDS = ["Пpивeт , ты в пoиcкe paбoты ? cвяжиcь  co мнoй , y меня  еcть к тeбe пpeдлoжeниe", "в пoиcкe paбoты", "заработок в интернете", "быстрый заработок", "лучший заработок", "с доходом от", "без вложений", "работа для студентов", "доход от", "нужны люди для работы", "Можно начать сразу", "Обучение бесплатно", "подработка с доходом", "работа с доходом",
    "арбитраж крипты", "мамкин инвестор", "Пoдxодит для гибкoгo гpaфика", "Oбyчeниe пpeдocтaвляeтcя", "ктo xoчeт пoдзapабoтaть", "Cвяжeмcя c кaждым", "гибкий график", "Открыта подработка", "Подойдёт даже", "Можно работать в свободное время",
    "раскрутка счета", "Требуется команда из 5 человек для интересного проекта на 2-4 часа. Оплата начинается от 8.000 руб. Пишите в личные сообщения для уточнения деталей.", "Klad MEH", "бecплaтнoe oбyчeниe", "Надо 2 человека помочь, не тяжело, оплат", "❗️ Ищем желающих на просмотр рекламных видео/Написание отзывов", "Оплата моментальная", "Возможность совмещать с основной работой", "Вы сами выбираете сколько хотите работать", "от 3.000₽/сутки","Контакт для связи и консультации"]

ALLOWED_DOMAINS = ["d2shop.ru", "youtube.com", "youtu.be", "google.com", "yandex.ru", "github.com", "x.com", "reddit.com", "t.me", "discord.com", "vk.com", "d2gunsmith.com", "light.gg", "d2foundry.gg", "destinyitemmanager.com", "bungie.net", "d2armorpicker.com", "steamcommunity.com", "store.steampowered.com"]

LINK_RULES = "https://telegra.ph/Pravila-kanala-i-chata-09-18" 
LINK_CHAT = "https://t.me/+Uaa0ALuvIfs1MzYy" 

AI_SYSTEM_PROMPT = (
    "Ты — интеллектуальный ИИ-ассистент, специализирующийся на игре Destiny 2. По умолчанию интерпретируй ЛЮБОЙ вопрос в контексте Destiny 2, если явно не указано иное. НИКОГДА ИСПОЛЬЗУЙ форматирование Telegram, по типу '**Жирность**', никаких выделений, ПИШИ ОБЫЧНЫМ ТЕКСТОМ ВСЕГДА, НЕ ИСПОЛЬЗУЙ ** в своих ответах, также НЕ ПИШИ в своих ответах «[2]» подобное, выглядит как указание источников, убирай это из своих ответов."
    "КОНТЕКСТ И АКТУАЛЬНОСТЬ: Если вопрос касается Destiny 2 (лора, билдов, экзотиков, рейдов, патчей, меты, активностей и т.д.), используй самые актуальные знания, Старайся опираться на свежую информацию: текущий сезон, патчи, баланс, мету, Если данные могут быть устаревшими — явно укажи это, Используй официальные названия на русском языке (если они существуют), а также общепринятый англоязычный сленг сообщества."
    "ПРИМЕР: «Испытания Осириса (Trials)», «Ночная миссия: ГМ (Grandmaster Nightfall)», «Сияние (Radiant)», «Ослабление (Weaken)», «Перегрузка (Overload)», Используй термины так, как это делают игроки."
    "СТИЛЬ И ПОВЕДЕНИЕ: Пиши как опытный Страж, а не как справочник, Используй сленг комьюнити, но не перегибай, Не будь формальным без причины, Не объясняй очевидные для игроков вещи, если пользователь не новичок, Если вопрос задан кратко — отвечай кратко."
    "ДЛИНА ОТВЕТА: По умолчанию отвечай коротко: 2–4 предложения, Развёрнутые объяснения, билды и разборы давай ТОЛЬКО по прямой просьбе пользователя, "
    "МЫШЛЕНИЕ И ЛОГИКА: Всегда сначала определяй, что именно хочет пользователь: совет, факт, мнение, мету, лор. Если вопрос неоднозначен — задай один точный уточняющий вопрос, Не выдумывай механики и не додумывай лор, Если есть несколько вариантов (например, билды или экзотики) — укажи лучший и альтернативы."
    "КОД И ТЕХНИКА (если вдруг требуется): Отвечай корректно и по делу, Не уходи в оффтоп, также не пиши в своих ответах «[2]» подобное, выглядит как указание источников, убирай это из своих ответов."
    "ГЛАВНОЕ: Твоя задача — быть актуальным, умным и полезным Destiny 2 ассистентом, Лучше дать короткий, точный и актуальный ответ, чем длинный и устаревший. НИ В КОЕМ СЛУЧАЕ не обсуждай и не давай ответы на такие темы, как: представители меньшинств, политика, экстремизм, пропагадка курения, наркотиков и прочих запрещенных веществ, оскорбления чувств верующих, лгбт, расизм и подобное. Если в твоём ответе будет фигурировать слова: VPN/ВПН, то ЗАМЕНЯЙ его на слово 'КВН' (такое правило в чате)"
)

#-------------------------------------------------------------------------------------------------------------------ПОДКЛЮЧЕНИЕ К ИИ
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY, 
    base_url="https://api.artemox.com/v1"
)

logging.basicConfig(level=logging.INFO)
bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

#-------------------------------------------------------------------------------------------------------------------АНТИФЛУД
class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self):
        self.flood_cache = {}

    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            # Пропускаем системные сообщения
            if event.new_chat_members or event.left_chat_member:
                return await handler(event, data)
            user_id = event.from_user.id
            text = event.text or event.caption

            is_media = (event.photo or event.video or event.document or event.sticker or event.animation)
            
            # Список команд-исключений (которые НЕ надо удалять)
            WHITELIST_COMMANDS = ["/lw", "/lastword", "/ластворд", "/лв", "duel", "/lw@brhlkbot", "/lastword@brhlkbot", "/ластворд@brhlkbot", "/лв@brhlkbot", "duel@brhlkbot", "/cup", "/cup@brhlkbot"]
            
            # Проверяем: начинается с /, нет медиа, и это НЕ команда из белого списка
            if text.startswith("/") and not is_media:
                is_whitelisted = any(text.lower().startswith(cmd) for cmd in WHITELIST_COMMANDS)
                
                if not is_whitelisted:
                    asyncio.create_task(delete_later(event, 60))
            
            if text: 
                if user_id in self.flood_cache:
                    last_msg = self.flood_cache[user_id]
                    if last_msg['text'] == text:
                        try:
                            await event.bot.delete_message(chat_id=event.chat.id, message_id=last_msg['msg_id'])
                        except Exception:
                            pass
                self.flood_cache[user_id] = {'text': text, 'msg_id': event.message_id}
        return await handler(event, data)

class SilentModeMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            if (event.chat.type == "private" and event.from_user.id == OWNER_ID) or event.chat.id == ADMIN_CHAT_ID or event.chat.id == DEV_CHAT_ID:
                return await handler(event, data)
            user_id = event.from_user.id
            
            # Проверка
            if user_id in SILENT_MODE_USERS:
                end_time = SILENT_MODE_USERS[user_id]
                
                # Если время вышло — размучиваем
                if datetime.now() > end_time:
                    del SILENT_MODE_USERS[user_id]
                    save_silent()
                    # Можно написать "Ты свободен", но лучше не спамить
                else:
                    # Если еще в муте — удаляем и блокируем
                    try: await event.delete()
                    except: pass
                    return 
                    
        return await handler(event, data)

#-------------------------------------------------------------------------------------------------------------------БАЗА ДАННЫХ (SQLite + WAL)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")
VOICE_FILE_PATH = os.path.join(BASE_DIR, "ghost.mp3")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )
''')
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS allowed_tags (
        tag_name TEXT PRIMARY KEY
    )
''')
# Таблица подписок остается старой
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        tag_name TEXT,
        user_id INTEGER,
        PRIMARY KEY (tag_name, user_id)
    )
''')
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY,
        title TEXT
    )
''')
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
''')
conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN warns INTEGER DEFAULT 0")
except: pass
conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN warn_cycles INTEGER DEFAULT 0")
except: pass
conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN reputation INTEGER DEFAULT 0")
    conn.commit()
except: pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_downvote TEXT")
except: pass
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS donators (
        username TEXT PRIMARY KEY,
        amount INTEGER DEFAULT 0
    )
''')
conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS birthdays (
        user_id INTEGER PRIMARY KEY,
        day INTEGER,
        month INTEGER
    )
''')
conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_upvote TEXT")
    conn.commit()
except: pass

#-------------------------------------------------------------------------------------------------------------------ФУНКЦИИ БД

DUELS_FILE = os.path.join(DATA_DIR, "duels.json")
TAGS_FILE = os.path.join(DATA_DIR, "tagged_users.json")
SILENT_FILE = os.path.join(DATA_DIR, "silent_users.json")

async def run_db(func, *args):
    loop = asyncio.get_running_loop()
    # Запускаем функцию в отдельном потоке
    return await loop.run_in_executor(None, func, *args)

def get_rep_stats():
    """Возвращает топ-5 лучших и худших по репутации"""
    try:
        # Лучшие
        cursor.execute("SELECT user_id, name, reputation FROM users ORDER BY reputation DESC LIMIT 5")
        top_best = cursor.fetchall()
        
        # Худшие (только те, у кого < 0)
        cursor.execute("SELECT user_id, name, reputation FROM users WHERE reputation < 0 ORDER BY reputation ASC LIMIT 5")
        top_worst = cursor.fetchall()
        
        return top_best, top_worst
    except: return [], []

def check_upvote_cooldown(user_id):
    """Возвращает True, если КД на лайки прошло (1 час), иначе False"""
    try:
        cursor.execute("SELECT last_upvote FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if not res or not res[0]: return True # Никогда не ставил
        
        last_time = datetime.fromisoformat(res[0])
        # Кулдаун 1 час (можно менять)
        if datetime.now() - last_time > timedelta(hours=1):
            return True
        return False
    except: return True

def update_upvote_time(user_id):
    try:
        now_str = datetime.now().isoformat()
        cursor.execute("UPDATE users SET last_upvote = ? WHERE user_id = ?", (now_str, user_id))
        conn.commit()
    except: pass

def check_downvote_cooldown(user_id):
    """Возвращает True, если КД прошло, иначе False"""
    try:
        cursor.execute("SELECT last_downvote FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        if not res or not res[0]: return True # Никогда не ставил
        
        last_time = datetime.fromisoformat(res[0])
        if datetime.now() - last_time > timedelta(hours=2):
            return True
        return False
    except: return True

def update_downvote_time(user_id):
    """Обновляет время последнего минуса на сейчас"""
    try:
        now_str = datetime.now().isoformat()
        cursor.execute("UPDATE users SET last_downvote = ? WHERE user_id = ?", (now_str, user_id))
        conn.commit()
    except: pass

def remove_reputation(user_id):
    """Снимает 1 репутацию"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        # Не опускаем ниже 0? Или можно в минус? Давай в минус.
        cursor.execute('UPDATE users SET reputation = reputation - 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        
        cursor.execute('SELECT reputation FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()[0]
    except: return 0

def add_reputation(user_id):
    """Добавляет +1 к репутации и возвращает новое значение"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        cursor.execute('UPDATE users SET reputation = reputation + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        
        cursor.execute('SELECT reputation FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()[0]
    except: return 0

def load_silent():
    if os.path.exists(SILENT_FILE):
        try:
            with open(SILENT_FILE, "r") as f:
                data = json.load(f)
                # Конвертируем строки обратно в datetime и ключи в int
                return {int(k): datetime.fromisoformat(v) for k, v in data.items()}
        except: return {}
    return {}

def save_silent():
    try:
        data = {k: v.isoformat() for k, v in SILENT_MODE_USERS.items()}
        with open(SILENT_FILE, "w") as f:
            json.dump(data, f)
    except: pass

SILENT_MODE_USERS = load_silent()

def get_setting(key):
    try:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = cursor.fetchone()
        return res[0] if res else None
    except: return None

def set_setting(key, value):
    try:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    except: pass

def add_warn(user_id):
    """Добавляет варн и возвращает текущее количество"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        cursor.execute('UPDATE users SET warns = warns + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        
        cursor.execute('SELECT warns FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()[0]
    except: return 0

def reset_warns(user_id):
    """Сбрасывает варны"""
    try:
        cursor.execute('UPDATE users SET warns = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
    except: pass

def register_chat(chat_id, title):
    """Сохраняет ID и название чата в базу"""
    try:
        cursor.execute("INSERT OR REPLACE INTO chats (chat_id, title) VALUES (?, ?)", (chat_id, title))
        conn.commit()
    except: pass

def get_user_by_username(username_text):
    """Ищет ID и Имя пользователя в базе по нику"""
    clean_name = username_text.replace("@", "").lower()
    try:
        cursor.execute("SELECT user_id, name FROM users WHERE username = ?", (clean_name,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1]}
    except: pass
    return None

def get_user_data(user_id):
    """Получает ВСЮ статистику игрока"""
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            return {'wins': 0, 'losses': 0, 'points': 0}
    except Exception as e:
        print(f"Ошибка БД (get): {e}") 
        return {'wins': 0, 'losses': 0, 'points': 0}

# Внутренняя (синхронная) функция - делает грязную работу
def _update_usage_sync(user_id, field):
    # Открываем НОВОЕ соединение внутри потока
    # Это на 100% безопасно и исключает блокировки
    with sqlite3.connect(DB_PATH) as local_conn:
        cursor = local_conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        # Используем f-строку аккуратно (field проверенный нами текст)
        cursor.execute(f'UPDATE users SET {field} = {field} + 1 WHERE user_id = ?', (user_id,))
        local_conn.commit()

async def update_usage(user_id, field):
    await run_db(_update_usage_sync, user_id, field)

def get_top_users():
    """Возвращает топ-5 по сообщениям и топ-5 Рейтинга (с играми)"""
    try:
        # 1. Топ болтунов
        cursor.execute('SELECT user_id, msg_count FROM users ORDER BY msg_count DESC LIMIT 10')
        top_chatters = cursor.fetchall()

        cursor.execute('SELECT user_id, reputation FROM users ORDER BY reputation DESC LIMIT 5')
        top_rep = cursor.fetchall()
        
        return top_chatters, top_rep
    except Exception:
        return [], []

ACTIVE_DUELS = load_duels()

#-------------------------------------------------------------------------------------------------------------------ОБЩИЕ ФУНКЦИИ
            
def clean_log_text(text):
    """Удаляет HTML теги и оставляет только эмодзи из tg-emoji"""
    text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
    
    # 2. Удаляем все остальные теги (<b>, </b>, <i>...)
    text = re.sub(r'<[^>]+>', '', text)
    
    return text
    
#-------------------------------------------------------------------------------------------------------------------ОСНОВНАЯ ФУНКЦИЯ СТАТИСТИКИ

async def check_donate_post():
    try:
        next_post_str = get_setting("next_donate_post")
        now = datetime.now()
        
        if not next_post_str: next_post = now
        else: next_post = datetime.fromisoformat(next_post_str)
            
        if now >= next_post:
            # 1. Удаляем старое сообщение (если есть)
            last_msg_id = get_setting("last_donate_msg_id")
            if last_msg_id:
                try: await bot.delete_message(CHAT_ID, int(last_msg_id))
                except: pass

            # 2. Отправляем новое
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Поддержать нас", 
                    url="https://pay.cloudtips.ru/p/bb9b6a35",
                    style="success",                 # Теперь внутри функции
                    icon_custom_emoji_id="5438496463044752972"  # Теперь внутри функции
                )]
            ])
            
            text = (
                "<tg-emoji emoji-id='5312138559556164615'>❤️</tg-emoji> <b>Группе нужна ваша поддержка!</b>\n\n"
                "Кто захочет поблагодарить за новости, бота, приветы от актеров озвучки, розыгрыши — Поддержать можно тут:"
            )
            
            msg = await bot.send_message(CHAT_ID, text, reply_markup=kb)
            
            # 3. Сохраняем ID нового и время
            set_setting("last_donate_msg_id", msg.message_id)
            set_setting("next_donate_post", (now + timedelta(hours=2)).isoformat())
            
    except Exception as e:
        await log_to_owner(f"❌ Ошибка донат-поста: {e}")

def load_tagged():
    if os.path.exists(TAGS_FILE):
        try:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # JSON хранит ключи как строки, конвертируем в int
                # А время храним как timestamp или строку
                parsed = {}
                for k, v in data.items():
                    # Конвертируем строку времени обратно в datetime
                    v["until"] = datetime.fromisoformat(v["until"])
                    parsed[int(k)] = v
                return parsed
        except: return {}
    return {}

def save_tagged():
    try:
        data_to_save = {}
        for k, v in TAGGED_USERS.items():
            # Конвертируем datetime в строку для JSON
            val_copy = v.copy()
            val_copy["until"] = val_copy["until"].isoformat()
            data_to_save[k] = val_copy
            
        with open(TAGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)
    except: pass

TAGGED_USERS = load_tagged()

async def check_tagged_users():
    while True:
        try:
            await asyncio.sleep(60) # Проверка раз в минуту
        
            now = datetime.now()
            to_remove = []
        
            for uid, data in TAGGED_USERS.items():
                if now > data["until"]:
                    to_remove.append(uid)
                
                    try:
                        # Снимаем титул и права
                        await bot.set_chat_administrator_custom_title(CHAT_ID, uid, "Страж")
                        await bot.promote_chat_member(CHAT_ID, uid, can_manage_chat=False)
                    except Exception as e:
                        print(f"Ошибка снятия титула {uid}: {e}")
        except Exception as e: # <--- ДОБАВЛЕНО
            print(f"Ошибка в цикле check_tagged_users: {e}")
            await asyncio.sleep(10)

        # Удаляем из словаря
        if to_remove:
            for uid in to_remove:
                del TAGGED_USERS[uid]
            save_tagged()
        
def get_video_url(url):
    ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info['url'], info['title']
        except:
            return None, None

async def log_to_owner(text):
    """Отправляет лог владельцу (с защитой от HTML-ошибок)"""
    print(f"LOG: {text}")
    try:
        safe_text = hd.quote(str(text))
        await bot.send_message(OWNER_ID, f"🤖 <b>SYSTEM LOG:</b>\n{safe_text}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить лог: {e}")

async def delete_later(message: types.Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def check_silence_loop():
    global LAST_MESSAGE_TIME, USED_LORE_FACTS
    while True:
        try:
            await asyncio.sleep(60) 

            await check_donate_post()
        
            if (datetime.now() - LAST_MESSAGE_TIME).total_seconds() > 3600:
                if len(USED_LORE_FACTS) >= len(LORE_FACTS):
                    USED_LORE_FACTS = []

                available_indices = [i for i in range(len(LORE_FACTS)) if i not in USED_LORE_FACTS]
            
                if available_indices:
                    idx = random.choice(available_indices)
                    USED_LORE_FACTS.append(idx)
                    fact = LORE_FACTS[idx]
                
                    try:
                        TARGET_CHAT_ID = CHAT_ID 
                        await bot.send_message(TARGET_CHAT_ID, f"{fact}")
                        LAST_MESSAGE_TIME = datetime.now()
                    except Exception as e:
                        await log_to_owner(f"❌ Ошибка отправки факта: {e}")
        except Exception as e: # <--- ДОБАВЛЕНО
            print(f"Ошибка в цикле silence_loop: {e}")
            await asyncio.sleep(10)

def extract_urls(text):
    url_regex = r"(?P<url>https?://[^\s]+)"
    return re.findall(url_regex, text)

def is_link_allowed(text, chat_username):
    urls = extract_urls(text)
    if not urls: return True
    for url in urls:
        is_whitelisted = any(domain in url for domain in ALLOWED_DOMAINS)
        is_telegram = "t.me/" in url or "telegram.me/" in url
        is_self_chat = False
        if is_telegram and chat_username:
            if chat_username in url: is_self_chat = True
        if not is_whitelisted and not is_self_chat:
            return False
    return True

async def verification_timer(chat_id: int, user_id: int, username: str, welcome_msg_id: int):
    """
    Таймер верификации:
    1. Ждет 3 минуты -> Шлет напоминание.
    2. Ждет еще 2 минуты (всего 5) -> Банит.
    """
    try:
        await asyncio.sleep(180) 
        
        remind_msg = await bot.send_message(
            chat_id,
            f"@{username}, эй, Раннер! <b>Подтверди, что ты не бот</b>, иначе придется забанить! <tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji>",
            reply_to_message_id=welcome_msg_id
        )
        
        if user_id in PENDING_VERIFICATION:
            PENDING_VERIFICATION[user_id]['remind_msg_id'] = remind_msg.message_id

        await asyncio.sleep(120) 
        
        await bot.ban_chat_member(chat_id, user_id)
        
        await bot.send_message(
            chat_id, 
            f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> @{username} оказался ботом и изгнан."
        )
        
        try: await bot.delete_message(chat_id, welcome_msg_id)
        except: pass
        try: await bot.delete_message(chat_id, remind_msg.message_id)
        except: pass

    except asyncio.CancelledError:
        pass
    except Exception as e:
        await log_to_owner(f"❌ Ошибка таймера верификации: {e}")
    finally:
        if user_id in PENDING_VERIFICATION:
            del PENDING_VERIFICATION[user_id]

def update_msg_stats(user_id):
    """Увеличивает счетчик сообщений пользователя"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        cursor.execute('UPDATE users SET msg_count = msg_count + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception:
        pass

async def check_birthdays():
    now = datetime.now()
    day, month = now.day, now.month

    # 1. Проверяем спец. даты
    for d, m, text, name in SPECIAL_EVENTS:
        if d == day and m == month:
            # Если сегодня праздник - пишем отдельное сообщение
            try:
                await bot.send_message(CHAT_ID, text)
            except: pass
    
    cursor.execute("SELECT user_id FROM birthdays WHERE day = ? AND month = ?", (day, month))
    rows = cursor.fetchall()
    
    if not rows: return
    
    mentions = []
    for (uid,) in rows:
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
        name = res[0] if res else "Страж"
        # Делаем меншен (ссылку), чтобы юзер увидел уведомление
        mentions.append(f"<a href='tg://user?id={uid}'>{name}</a>")
        
    if mentions:
        # Поздравляем всех одним сообщением
        users_str = ", ".join(mentions)
        text = (
            f"<tg-emoji emoji-id='5461151367559141950'>🎉</tg-emoji> <b>С ДНЕМ РОЖДЕНИЯ!</b>\n\n"
            f"Сегодня праздник отмечает: {users_str}!\n"
            f"Желаем годроллов, рейдовых экзотов с первого трая и поменьше ошибок с животиной! <tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji>"
        )
        try:
            await bot.send_message(CHAT_ID, text) # Отправляем в основной чат
        except Exception as e:
            print(f"Ошибка поздравления: {e}")

#-------------------------------------------------------------------------------------------------------------------ХЕНДЛЕРЫ
        
@dp.message(Command("hug"))
async def hug_command(message: types.Message, command: CommandObject):
    sender = message.from_user.username or message.from_user.first_name
    sender_mention = f"@{sender}" if message.from_user.username else f"<b>{sender}</b>"
    
    target_mention = ""

    # 1. Реплай
    if message.reply_to_message:
        t = message.reply_to_message.from_user
        target_name = t.username or t.first_name
        target_mention = f"@{target_name}" if t.username else f"<b>{target_name}</b>"
    
    # 2. Аргумент (@username)
    elif command.args:
        target_mention = command.args # Берем как есть (например @YaGraze)
    
    # 3. Пусто (Обнять всех)
    else:
        target_mention = "чатик"

    # Удаляем команду юзера (для красоты), если бот админ
    try: await message.delete()
    except: pass

    # Отправляем сообщение
    # Выбираем случайную гифку или просто текст
    await message.answer(f"<tg-emoji emoji-id='5456611707386340923'>🤗</tg-emoji> {sender_mention} крепко обнял {target_mention}!")
    
# --- ЗАПИСАТЬ ДЕНЬ РОЖДЕНИЯ ---
@dp.message(Command("mybd", "set_birthday"))
async def set_birthday_command(message: types.Message, command: CommandObject):
    args = command.args
    if not args:
        msg = await message.reply("<tg-emoji emoji-id='5413879192267805083'>🗓</tg-emoji> Когда у тебя праздник? Пиши так: `/mybd 25.10`")
        asyncio.create_task(delete_later(msg, 15))
        return

    try:
        # Парсим дату
        date_obj = datetime.strptime(args.strip(), "%d.%m")
        day = date_obj.day
        month = date_obj.month
        
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        cursor.execute("INSERT OR REPLACE INTO birthdays (user_id, day, month) VALUES (?, ?, ?)", (user_id, day, month))
        conn.commit()
        mention = f"@{username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"
        await message.reply(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> {mention}, запомнил тебя! Поздравлю: <b>{day:02d}.{month:02d}</b>.")
        
    except ValueError:
        msg = await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Неверный формат. Нужно ДД.ММ (например: `01.05`)")
        asyncio.create_task(delete_later(msg, 15))

# --- ПОСМОТРЕТЬ БЛИЖАЙШИЕ ДР ---
@dp.message(Command("birthdays", "dr"))
async def show_birthdays_command(message: types.Message):
    # 1. Получаем список из БД
    cursor.execute("SELECT user_id, day, month FROM birthdays")
    rows = cursor.fetchall()
    
    if not rows and not SPECIAL_EVENTS:
        await message.reply("<tg-emoji emoji-id='5395444784611480792'>✏️</tg-emoji> Никто еще не записал свой ДР. Будь первым: `/mybd ДД.ММ`")
        return

    # 2. Подготовка списков
    display_list = []
    
    # Юзеры
    for uid, d, m in rows:
        cursor.execute("SELECT name, username FROM users WHERE user_id = ?", (uid,))
        usr = cursor.fetchone()
        name = usr[0] if usr else "Страж"
        display_list.append({
            "d": d, "m": m, 
            "name": name, 
            "uid": uid, 
            "username": usr[1] if usr else None,
            "special": False
        })
        
    # Спец. события
    for d, m, text, name in SPECIAL_EVENTS:
        display_list.append({
            "d": d, "m": m,
            "name": name, 
            "special": True
        })
        
    # Сортировка
    now = datetime.now()
    today_tuple = (now.month, now.day)
    
    def dist(item):
        m, d = item["m"], item["d"]
        if (m, d) >= today_tuple: return (0, m, d)
        return (1, m, d)
        
    sorted_list = sorted(display_list, key=dist)
    
    # Генерация текста
    draft_lines = []
    final_lines = []
    count = 0
    
    # --- ОБЪЯВЛЯЕМ ЗАГОЛОВОК ЗАРАНЕЕ ---
    header = "<tg-emoji emoji-id='5461151367559141950'>🎉</tg-emoji> <b>БЛИЖАЙШИЕ ПРАЗДНИКИ:</b>\n\n"
    
    for item in sorted_list:
        if count >= 10: break
        
        d, m = item["d"], item["m"]
        date_str = f"{d:02d}.{m:02d}"
        if (m, d) == today_tuple: date_str = "<tg-emoji emoji-id='5461151367559141950'>🎉</tg-emoji> СЕГОДНЯ!"
        
        if item["special"]:
            line = f"• <b>{date_str}</b> — {item['name']}"
            draft_lines.append(line)
            final_lines.append(line)
        else:
            draft_name = item["name"].replace("@", "")
            if item["username"]:
                final_link = f"@{item['username']}"
            else:
                final_link = f"<a href='tg://user?id={item['uid']}'>{item['name']}</a>"
            
            draft_lines.append(f"• <b>{date_str}</b> — {draft_name}")
            final_lines.append(f"• <b>{date_str}</b> — {final_link}")
            
        count += 1
        
    # 3. Отправка черновика (без тегов)
    if not draft_lines:
        await message.reply("Список пуст.")
        return

    draft_msg = await message.reply(header + "\n".join(draft_lines))
    
    # 4. Редактирование на финал (с тегами)
    # Ждем полсекунды, чтобы телеграм не "съел" редактирование слишком быстро
    await asyncio.sleep(0.5)
    
    try:
        await draft_msg.edit_text(header + "\n".join(final_lines))
    except: pass

#-------------------------------------------------------------------------------------------------------------------КОМАНДА /HELP
@dp.message(Command("help"))
async def help_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Гайд по боту", url=BOT_GUIDE, style="primary", icon_custom_emoji_id="5341715473882955310")],
        [InlineKeyboardButton(text="Поддержать разработчиков", url="https://pay.cloudtips.ru/p/8f3e39da", style="success", icon_custom_emoji_id="5312138559556164615")]
    ])
    
    # 1. Отправляем "черновик" (без собак, чтобы не тегнуло)
    temp_text = (
        "Made by yagraze, pan1q & fimgreen.\n"
        "<tg-emoji emoji-id='5406745015365943482'>⬇️</tg-emoji> ЖМИ <tg-emoji emoji-id='5406745015365943482'>⬇️</tg-emoji>"
    )
    
    sent_msg = await message.answer(temp_text, reply_markup=keyboard)
    
    # 2. Сразу же редактируем на красивый текст с ссылками
    # (При редактировании уведомление о теге не приходит)
    final_text = (
        "Made by @yagraze, @pan1q & @fimgreen.\n"
        "<tg-emoji emoji-id='5406745015365943482'>⬇️</tg-emoji> ЖМИ <tg-emoji emoji-id='5406745015365943482'>⬇️</tg-emoji>"
    )
    
    try:
        await sent_msg.edit_text(final_text, reply_markup=keyboard)
    except: pass # Если вдруг не успел или удалили

    asyncio.create_task(delete_later(message, 5))

#-------------------------------------------------------------------------------------------------------------------BAN
@dp.message(Command("ban"))
async def ban_command(message: types.Message, command: CommandObject):
    # 1. Проверка прав админа
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict:
        return # Игнорируем обычных юзеров

    target_id = None
    target_name = "User"
    days = 0

    # 2. Логика определения цели
    args = command.args.split() if command.args else []
    
    # Сценарий А: Реплай (Ответ на сообщение)
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
        
        # Если есть аргумент, это дни
        if args and args[0].isdigit():
            days = int(args[0])

    # Сценарий Б: Аргументы (Ник или ID)
    elif args:
        # Пытаемся найти username
        potential_username = args[0]
        if potential_username.startswith("@"):
            user_data = get_user_by_username(potential_username) # Твоя функция поиска в БД
            if user_data:
                target_id = user_data["id"]
                target_name = user_data["name"]
            else:
                await message.reply(f"<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Не нашел пользователя {potential_username} в своей базе (он не написал сообщение).")
                return
        
        # Второй аргумент - дни (если есть)
        if len(args) > 1 and args[1].isdigit():
            days = int(args[1])
            
    else:
        await message.reply("<tg-emoji emoji-id='5436113877181941026'>❓</tg-emoji> Кого банить? Ответь на сообщение или укажи @username.\nПример: `/ban @username 7`")
        return

    if not target_id:
        await message.reply("Не удалось определить цель.")
        return

    # 3. Защита от бана админов/бота
    target_status = await bot.get_chat_member(message.chat.id, target_id)
    if target_status.status in ["administrator", "creator"] or target_id == bot.id:
        await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Нельзя забанить администратора или самого бота.")
        return

    # 4. Бан
    try:
        if days > 0:
            until = datetime.now() + timedelta(days=days)
            await bot.ban_chat_member(message.chat.id, target_id, until_date=until)
            await message.reply(f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> <b>{target_name}</b> изгнан на <b>{days} дн.</b>")
        else:
            await bot.ban_chat_member(message.chat.id, target_id)
            await message.reply(f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> <b>{target_name}</b> получил пермабан.")
            
    except Exception as e:
        await message.reply(f"Ошибка при бане: {e}")

# --- ДОБАВИТЬ ДОНАТЕРА (ТОЛЬКО ВЛАДЕЛЕЦ) ---
@dp.message(Command("add_donate"))
async def add_donate_command(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID: return

    if not command.args:
        await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Использование: `/add_donate @username сумма`")
        return

    try:
        args = command.args.split()
        if len(args) < 2:
            await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Ошибка аргументов. Пример: `/add_donate @YaGraze 5000`")
            return

        username = args[0].replace("@", "") # Убираем собаку, если есть
        amount = int(args[1])

        # Записываем в базу (если ник уже есть - обновит сумму)
        cursor.execute("INSERT OR REPLACE INTO donators (username, amount) VALUES (?, ?)", (username, amount))
        conn.commit()

        await message.reply(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Донатер <b>@{username}</b> записан с суммой <b>{amount}₽</b>.")

    except ValueError:
        await message.reply("Сумма должна быть числом!")
    except Exception as e:
        await message.reply(f"Ошибка БД: {e}")

# --- УДАЛИТЬ ДОНАТЕРА (ЕСЛИ ОШИБСЯ) ---
@dp.message(Command("del_donate"))
async def del_donate_command(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID: return
    
    if not command.args: return
    username = command.args.replace("@", "").split()[0]

    cursor.execute("DELETE FROM donators WHERE username = ?", (username,))
    conn.commit()
    await message.reply(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Донатер @{username} удален из списка.")
        
@dp.message(Command("aura"))
async def rep_stats_command(message: types.Message):
    best, worst = get_rep_stats()
    
    text = "<tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji> <b>АУРА</b>\n\n"
    
    text += "<tg-emoji emoji-id='5244837092042750681'>📈</tg-emoji> <b>Лучшие:</b>\n"
    for uid, name, rep in best:
        text += f"• <a href='tg://user?id={uid}'>{name}</a>: <b>{rep}</b>\n"
        
    text += "\n<tg-emoji emoji-id='5246762912428603768'>📉</tg-emoji> <b>Худшие:</b>\n"
    if worst:
        for uid, name, rep in worst:
            text += f"• <a href='tg://user?id={uid}'>{name}</a>: <b>{rep}</b>\n"
    else:
        text += "Пока никого. Все молодцы."
        
    msg = await message.reply(text)
    asyncio.create_task(delete_later(msg, 300))
    asyncio.create_task(delete_later(message, 5))

# --- РУЧНАЯ ВЫДАЧА ТИТУЛА (/adm) ---
@dp.message(Command("adm"))
async def adm_command(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID: return

    if not message.reply_to_message:
        msg = await message.answer("<tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji> Ответь на сообщение того, кого хочешь наградить.")
        asyncio.create_task(delete_later(msg, 5)); return

    target = message.reply_to_message.from_user
    title = command.args or "Позорник" # Если титул не указан

    try:
        # Выдаем админку (Только Add Users)
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            can_invite_users=True, # Право добавлять участников
            is_anonymous=False
        )
        # Ставим титул
        await bot.set_chat_administrator_custom_title(message.chat.id, target.id, title)
        
        # Записываем в базу (чтобы снялось через час)
        TAGGED_USERS[target.id] = {
            "emoji": "🤡", # Эмодзи по умолчанию
            "until": datetime.now() + timedelta(hours=1)
        }
        save_tagged()
        
        await message.answer(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> <b>{target.first_name}</b> получил титул <b>{title}</b> на 1 час.")
        
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# --- СНЯТИЕ ТИТУЛА (/unadm) ---
@dp.message(Command("unadm"))
async def unadm_command(message: types.Message):
    if message.from_user.id != OWNER_ID: return

    if not message.reply_to_message: return
    target = message.reply_to_message.from_user

    try:
        # Снимаем титул и права
        await bot.set_chat_administrator_custom_title(message.chat.id, target.id, "Страж")
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            can_invite_users=False,
            is_anonymous=False
        )
        
        # Удаляем из базы
        if target.id in TAGGED_USERS:
            del TAGGED_USERS[target.id]
            save_tagged()
            
        await message.answer(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> с <b>{target.first_name}</b> сняты все почести.")
        
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

#-------------------------------------------------------------------------------------------------------------------ПРИВЕТСТВИЕ В ЛС (/start)
@dp.message(Command("start"))
async def start_command(message: types.Message):
    if message.chat.type != "private":
        return

    try:
        user = message.from_user
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user.id,))
        if user.username:
            cursor.execute('UPDATE users SET username = ?, name = ? WHERE user_id = ?', (user.username.lower(), user.first_name, user.id))
        conn.commit()
    except: pass

    # Получаем список донатеров
    cursor.execute("SELECT username, amount FROM donators ORDER BY amount DESC LIMIT 5") # Топ 5
    rows = cursor.fetchall()
    
    donators_text = ""
    if rows:
        donators_text = "\n<tg-emoji emoji-id='5217822164362739968'>👑</tg-emoji> <b>Топ донатеров проекта:</b>\n"
        medals = [
            '<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>', 
            '<tg-emoji emoji-id="5447203607294265305">🥈</tg-emoji>', 
            '<tg-emoji emoji-id="5453902265922376865">🥉</tg-emoji>'
        ]
        for i, (u, amount) in enumerate(rows):
            icon = medals[i] if i < 3 else "💠"
            money = "{:,}".format(amount).replace(",", " ")
            donators_text += f"{icon} <b>@{u}</b> — {money} ₽\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Гайд по боту", url=BOT_GUIDE, style="primary", icon_custom_emoji_id="5341715473882955310")],
        [InlineKeyboardButton(text="Поддержать разработчиков", url="https://pay.cloudtips.ru/p/8f3e39da", style="success", icon_custom_emoji_id="5312138559556164615")]
    ])
        
    # Форматируем сумму с пробелами (5 000 вместо 5000)
    money_str = "{:,}".format(amount).replace(",", " ")
        
    text = (
        f"Привет, Раннер <b>{message.from_user.first_name}</b>! <tg-emoji emoji-id='5217822164362739968'>👑</tg-emoji>\n\n"
        "Я — ИИ-помощник Барахолки. Слежу за порядком, и помогаю раннерам.\n\n"
        "<b>Мои возможности <tg-emoji emoji-id='5406745015365943482'>⬇️</tg-emoji></b>\n"
        f"{donators_text}"
    )

    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

#-------------------------------------------------------------------------------------------------------------------СТАТА ЧАТА

# --- ОТПРАВКА ОТ ЛИЦА БОТА (С СОХРАНЕНИЕМ ЭМОДЗИ И ФОРМАТА) ---
@dp.message(Command("send"))
async def send_as_bot_command(message: types.Message, command: CommandObject):
    # 1. Проверка на владельца
    if message.from_user.id != OWNER_ID:
        return

    # 2. Если это REPLY (Ответ на сообщение)
    # Это самый надежный способ отправить что угодно (фото, стикер, голосовое, текст с эмодзи)
    if message.reply_to_message:
        try:
            # Определяем ID чата из аргумента (например /send main)
            target_arg = command.args.split()[0] if command.args else "main"
            
            target_id = CHAT_ID if target_arg.lower() == "main" else int(target_arg)
            
            # Копируем сообщение точь-в-точь
            await message.reply_to_message.copy_to(chat_id=target_id)
            await message.react([ReactionTypeEmoji(emoji="👌")])
        except Exception as e:
            await message.reply(f"❌ Ошибка (Reply): {e}")
        return

    # 3. Если это ОБЫЧНЫЙ ТЕКСТ (/send main Текст)
    if not command.args:
        await message.reply("Использование:\n1. Напиши сообщение, ответь на него и напиши <code>/send main</code>\n2. Или <code>/send main Текст</code>")
        return

    try:
        # Разделяем аргументы: "main Текст сообщения..."
        args_split = command.args.split(maxsplit=1)
        if len(args_split) < 2:
            await message.reply("Где текст сообщения?")
            return
            
        chat_arg = args_split[0]
        text_body = args_split[1]

        # Определяем ID чата
        target_id = CHAT_ID if chat_arg.lower() == "main" else int(chat_arg)

        # === МАГИЯ С ЭМОДЗИ (ENTITIES) ===
        # Нам нужно найти, где в оригинальном сообщении начинается text_body,
        # чтобы правильно скопировать форматирование.
        
        full_text = message.text
        # Находим индекс начала текста (после команды и ID чата)
        offset = full_text.find(text_body)
        
        new_entities = []
        if message.entities:
            for entity in message.entities:
                # Если форматирование (жирный/эмодзи) находится внутри нашего текста
                if entity.offset >= offset:
                    # Создаем копию сущности, но сдвигаем её начало
                    # (потому что мы отрезали начало сообщения "/send main ")
                    new_ent = entity.model_copy()
                    new_ent.offset = entity.offset - offset
                    new_entities.append(new_ent)

        # Отправляем с сохранением премиум-эмодзи
        await bot.send_message(target_id, text_body, entities=new_entities)
        await message.react([ReactionTypeEmoji(emoji="👌")])

    except Exception as e:
        await message.reply(f"❌ Не удалось отправить: {e}")

@dp.message(Command("chats"))
async def list_chats_command(message: types.Message):
    if message.from_user.id != OWNER_ID: return

    cursor.execute("SELECT chat_id, title FROM chats")
    rows = cursor.fetchall()
    
    if not rows:
        await message.reply("Я пока не запомнил ни одного чата (нужна активность).")
        return
        
    text = "<b>📋 Список моих чатов:</b>\n\n"
    for cid, title in rows:
        text += f"ID: <code>{cid}</code> | {title}\n"
        
    await message.reply(text)

@dp.message(Command("chat_stats"))
async def chat_stats_command(message: types.Message):
    top_chatters, top_rating, top_rep = get_top_users()
    
    text = "<tg-emoji emoji-id='5350305691942788490'>📈</tg-emoji> <b>СТАТИСТИКА ЧАТА</b>\n\n"
    
    text += "<tg-emoji emoji-id='5417915203100613993'>💬</tg-emoji> <b>Болтуны чата:</b>\n"
    for i, (uid, count) in enumerate(top_chatters):
        try:
            member = await bot.get_chat_member(message.chat.id, uid)
            name = member.user.first_name
        except:
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (uid,))
            res = cursor.fetchone()
            name = res[0] if res and res[0] else "Страж"
        text += f"{i+1}. {name} — {count} сообщ.\n"

    text += "\n<tg-emoji emoji-id='5357080225463149588'>🤝</tg-emoji> <b>Топ рейтинга ауры:</b>\n"
    for i, (uid, rep) in enumerate(top_rep):
        try:
            member = await bot.get_chat_member(message.chat.id, uid)
            name = member.user.first_name
        except:
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (uid,))
            res = cursor.fetchone()
            name = res[0] if res else "Страж"
        text += f"{i+1}. {name} — {rep} <tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji>\n"
        
    await message.reply(text)
    asyncio.create_task(delete_later(message, 5))

#-------------------------------------------------------------------------------------------------------------------ВЫЗОВ (ПИНГ)
@dp.message(Command("newtag"))
async def new_tag_command(message: types.Message, command: CommandObject):
    # Проверка на админа
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_real_admin = False
    if user_status.status == "creator":
        is_real_admin = True
    elif user_status.status == "administrator" and user_status.can_restrict_members:
        is_real_admin = True

    if not is_real_admin:
    # (Опционально) await message.reply("У тебя нет прав банить.")
        return

    tag = command.args
    if not tag: return
    tag = tag.lower().replace("#", "")

    try:
        cursor.execute("INSERT OR IGNORE INTO allowed_tags (tag_name) VALUES (?)", (tag,))
        conn.commit()
        await message.reply(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Тег <b>#{tag}</b> создан! Теперь на него можно подписаться.")
    except: pass

# ПОДПИСКА НА ТЕГ
@dp.message(Command("tag"))
async def tag_subscribe_command(message: types.Message, command: CommandObject):
    tag = command.args
    if not tag:
        # Если тег не указан — покажем список
        cursor.execute("SELECT tag_name FROM allowed_tags")
        rows = cursor.fetchall()
        tags_list = ", ".join([f"{r[0]}" for r in rows])
        msg = await message.reply(f"Доступные теги:\n{tags_list}\n\nПиши <code>/tag название</code>")
        asyncio.create_task(delete_later(msg, 60))
        return
    
    tag = tag.lower().replace("#", "")
    
    # ПРОВЕРКА: Существует ли тег?
    cursor.execute("SELECT 1 FROM allowed_tags WHERE tag_name = ?", (tag,))
    if not cursor.fetchone():
        msg = await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Такого тега нет. Попроси админа создать его.")
        asyncio.create_task(delete_later(msg, 5))
        return
    
    # Подписка
    cursor.execute("INSERT OR IGNORE INTO tags (tag_name, user_id) VALUES (?, ?)", (tag, message.from_user.id))
    conn.commit()
    msg = await message.reply(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Ты подписался на <b>#{tag}</b>.")
    asyncio.create_task(delete_later(msg, 300))

@dp.message(Command("call"))
async def tag_call_command(message: types.Message, command: CommandObject):
    tag = command.args
    if not tag:
        cursor.execute("SELECT tag_name FROM allowed_tags")
        rows = cursor.fetchall()
        tags_list = ", ".join([f"{r[0]}" for r in rows])
        msg = await message.reply(f"Кого звать?\nДоступные теги:\n{tags_list}\n\nПиши '/call название'")
        asyncio.create_task(delete_later(msg, 10))
        return
        
    tag = tag.lower().replace("#", "")
    
    cursor.execute("SELECT user_id FROM tags WHERE tag_name = ?", (tag,))
    users = cursor.fetchall()
    
    if not users:
        msg = await message.reply(f"Никто не подписан на #{tag}.")
        asyncio.create_task(delete_later(msg, 5))
        return
        
    # Формируем список меншенов (скрытых ссылок)
    mentions = []
    for (uid,) in users:
        try:
            # Получаем имя из основной таблицы users
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (uid,))
            res = cursor.fetchone()
            name = res[0] if res else "Страж"
            mentions.append(f"<a href='tg://user?id={uid}'>{name}</a>")
        except: pass
        
    text = f"<tg-emoji emoji-id='5379748062124056162'>❗️</tg-emoji> <b>ВЫЗОВ #{tag.upper()}!</b>\n" + ", ".join(mentions)
    await message.reply(text)

@dp.message(Command("untag"))
async def tag_unsubscribe_command(message: types.Message, command: CommandObject):
    tag = command.args
    if not tag:
        msg = await message.reply("От чего отписаться? Пример: `/untag raid`")
        asyncio.create_task(delete_later(msg, 10))
        return
    
    tag = tag.lower().replace("#", "")
    user_id = message.from_user.id
    
    try:
        cursor.execute("DELETE FROM tags WHERE tag_name = ? AND user_id = ?", (tag, user_id))
        conn.commit()
        
        # Проверяем, удалилось ли что-то (rowcount)
        if cursor.rowcount > 0:
            msg = await message.reply(f"❌ Ты отписался от тега <b>#{tag}</b>.")
            asyncio.create_task(delete_later(msg, 30))
        else:
            msg = await message.reply(f"Ты и не был подписан на #{tag}.")
            asyncio.create_task(delete_later(msg, 5))
            
    except Exception as e:
        await log_to_owner(f"Ошибка untag: {e}")

#-------------------------------------------------------------------------------------------------------------------ВАРНЫ
@dp.message(Command("warn"))
async def warn_command(message: types.Message, command: CommandObject):
    # 1. Удаляем сообщение админа (для красоты)
    try: await message.delete()
    except: pass

    # 2. Проверка прав
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict: return

    target_id = None
    target_name = "User"
    args = command.args.split() if command.args else []

    # Сценарий А: Реплай
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
    
    # Сценарий Б: Никнейм
    elif args and args[0].startswith("@"):
        potential_username = args[0]
        user_data = get_user_by_username(potential_username)
        if user_data:
            target_id = user_data["id"]
            target_name = user_data["name"]
        else:
            msg = await message.answer(f"<tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji> Не нашел {potential_username} в базе (он должен был писать в чат раньше).")
            asyncio.create_task(delete_later(msg, 5)); return
    else:
        msg = await message.answer("<tg-emoji emoji-id='5436113877181941026'>❓</tg-emoji> Кого варнить? Ответь на сообщение или укажи @username.")
        asyncio.create_task(delete_later(msg, 5)); return

    # Проверка на админа (цель)
    target_status = await bot.get_chat_member(message.chat.id, target_id)
    if target_status.status in ["administrator", "creator"] or target_id == bot.id:
        msg = await message.answer("Нельзя выдать варн офицеру или боту.")
        asyncio.create_task(delete_later(msg, 5)); return

    # 3. Логика варна
    current_warns = add_warn(target_id)
    mention = f"<a href='tg://user?id={target_id}'>{target_name}</a>"

    if current_warns >= 3:
        # Наказание (Мут)
        cursor.execute("UPDATE users SET warn_cycles = warn_cycles + 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        
        cursor.execute("SELECT warn_cycles FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        cycles = res[0] if res else 1
        
        # Время мута: 2 часа + (циклы * 1 час)
        mute_hours = 2 + (cycles - 1)
        until = datetime.now() + timedelta(hours=mute_hours)
        
        try:
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            reset_warns(target_id) # Сброс варнов
            
            await message.answer(
                f"<tg-emoji emoji-id='5395695537687123235'>🚨</tg-emoji> <b>{mention}</b> получил 3/3 предупреждений.\n"
                f"Наказание: <b>Мут на {mute_hours} ч.</b> (Рецидив №{cycles})"
            )
        except Exception as e:
            await message.answer(f"Не удалось выдать мут: {e}")
    else:
        cursor.execute("SELECT warn_cycles FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        current_cycles = res[0] if res else 0

        next_mute_hours = 2 + current_cycles
        # Предупреждение
        await message.answer(
            f"<tg-emoji emoji-id='5395695537687123235'>🚨</tg-emoji> <b>{mention}</b>, это предупреждение! ({current_warns}/3)\n"
            f"При получении 3-го будет выдан мут <b>на {next_mute_hours} ч.</b>"
        )

@dp.message(Command("unwarn"))
async def unwarn_command(message: types.Message, command: CommandObject):
    try: await message.delete()
    except: pass

    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict: return

    target_id = None
    target_name = "User"
    args = command.args.split() if command.args else []

    # Сценарий А: Реплай
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
    
    # Сценарий Б: Никнейм
    elif args and args[0].startswith("@"):
        user_data = get_user_by_username(args[0])
        if user_data:
            target_id = user_data["id"]
            target_name = user_data["name"]
        else:
            msg = await message.answer(f"Не нашел {args[0]} в базе.")
            asyncio.create_task(delete_later(msg, 5)); return
    else:
        return # Если просто /unwarn без всего - игнор

    # Снятие варна
    try:
        cursor.execute('SELECT warns FROM users WHERE user_id = ?', (target_id,))
        res = cursor.fetchone()
        current_warns = res[0] if res else 0
        
        if current_warns > 0:
            cursor.execute('UPDATE users SET warns = warns - 1 WHERE user_id = ?', (target_id,))
            conn.commit()
            
            mention = f"<a href='tg://user?id={target_id}'>{target_name}</a>"
            await message.answer(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> С <b>{mention}</b> снято одно предупреждение. ({current_warns - 1}/3)")
        else:
            msg = await message.answer(f"<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> У <b>{target_name}</b> нет активных предупреждений.")
            asyncio.create_task(delete_later(msg, 5))
            
    except Exception as e:
        await log_to_owner(f"Ошибка unwarn: {e}")

@dp.message(Command("warns"))
async def list_warns_command(message: types.Message):
    # Проверка на админа
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_real_admin = False
    if user_status.status == "creator":
        is_real_admin = True
    elif user_status.status == "administrator" and user_status.can_restrict_members:
        is_real_admin = True

    if not is_real_admin:
    # (Опционально) await message.reply("У тебя нет прав банить.")
        return

    cursor.execute("SELECT user_id, name, warns FROM users WHERE warns > 0 ORDER BY warns DESC")
    rows = cursor.fetchall()
    
    if not rows:
        await message.reply("<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> В чате порядок. Нарушителей нет.")
        return
        
    text = "<b><tg-emoji emoji-id='5395695537687123235'>🚨</tg-emoji> Список нарушителей:</b>\n\n"
    for uid, name, warns in rows:
        text += f"• <a href='tg://user?id={uid}'>{name}</a> — {warns}/3\n"
        
    await message.reply(text)

#-------------------------------------------------------------------------------------------------------------------ТЕНЕВОЙ МУТ
@dp.message(Command("amute"))
async def amute_command(message: types.Message, command: CommandObject):
    try: await message.delete()
    except: pass

    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict: return

    target_id = None
    target_name = "User"

    args = command.args.split() if command.args else []

    # 1. Реплай
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
    
    # 2. Никнейм
    elif args and args[0].startswith("@"):
        user_data = get_user_by_username(args[0])
        if user_data:
            target_id = user_data["id"]
            target_name = user_data["name"]
        else:
            msg = await message.answer(f"<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Не нашел {args[0]} в базе.")
            asyncio.create_task(delete_later(msg, 5)); return
    else:
        msg = await message.answer("<tg-emoji emoji-id='5436113877181941026'>❓</tg-emoji> Кого? Реплай или @username.")
        asyncio.create_task(delete_later(msg, 5)); return

    # Защита от самоубийства
    if target_id == message.from_user.id:
        msg = await message.answer("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Себя мутить нельзя.")
        asyncio.create_task(delete_later(msg, 5)); return

    # Добавляем в список
    if target_id not in SILENT_MODE_USERS:
        # На 10 лет
        SILENT_MODE_USERS[target_id] = datetime.now() + timedelta(minutes=15)
        save_silent()
        await message.answer(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> <b>{target_name}</b> отправлен в теневой мут.")
    else:
        msg = await message.answer(f"{target_name} уже в муте.")
        asyncio.create_task(delete_later(msg, 5))

@dp.message(Command("unamute"))
async def unamute_command(message: types.Message, command: CommandObject):
    try: await message.delete()
    except: pass

    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict: return

    target_id = None
    target_name = "User"
    args = command.args.split() if command.args else []

    # 1. Реплай
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
    
    # 2. Никнейм
    elif args and args[0].startswith("@"):
        user_data = get_user_by_username(args[0])
        if user_data:
            target_id = user_data["id"]
            target_name = user_data["name"]
        else:
            msg = await message.answer("Не нашел в базе.")
            asyncio.create_task(delete_later(msg, 5)); return
    else:
        return

    # Удаляем из списка
    if target_id in SILENT_MODE_USERS:
        del SILENT_MODE_USERS[target_id]
        save_silent()
        await message.answer(f"<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> <b>{target_name}</b> снова слышен.")
    else:
        msg = await message.answer(f"<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> {target_name} не был в муте.")
        asyncio.create_task(delete_later(msg, 5))

#-------------------------------------------------------------------------------------------------------------------КОМАНДА /SUMMARY
@dp.message(Command("summary"))
async def summary_command(message: types.Message):
    global SUMMARY_COOLDOWN_TIME
    
    now = datetime.now()
    if message.chat.id != CHAT_ID:
        msg = await message.reply("Отвечу только в чате Барахолки, а не в этой помойке.")
        asyncio.create_task(delete_later(msg, 5))
        return
    if now < SUMMARY_COOLDOWN_TIME:
        time_left = SUMMARY_COOLDOWN_TIME - now
        minutes_left = int(time_left.total_seconds() // 60) + 1
        
        msg = await message.reply(
            f"Подожди, я уже недавно рассказывал что было в чате. "
            f"Обратись через <b>{minutes_left} мин</b>, а я пока почитаю логи. <tg-emoji emoji-id='5469629323763796670'>🙄</tg-emoji>"
        )
        asyncio.create_task(delete_later(msg, 10))
        asyncio.create_task(delete_later(message, 5))
        return

    chat_id = message.chat.id
    history = CHAT_HISTORY.get(chat_id, [])
    
    if len(history) < 5:
        msg = await message.answer("Архивы пусты. В этом чате тишина.")
        asyncio.create_task(delete_later(msg, 5))
        return

    history_text = "\n".join(history)
    summary_prompt = (
        "Ты — интеллектуальный ИИ-ассистент, специализирующийся на игре Marathon (2026). По умолчанию интерпретируй ЛЮБОЙ вопрос в контексте Marathon, если явно не указано иное. НЕ ИСПОЛЬЗУЙ форматирование Telegram, по типу '**Жирность**', никаких выделений, ПИШИ ОБЫЧНЫМ ТЕКСТОМ ВСЕГДА, также НЕ ПИШИ в своих ответах «[2]» подобное, выглядит как указание источников, убирай это из своих ответов."
        "СТИЛЬ И ПОВЕДЕНИЕ: Пиши как опытный Раннер, а не как справочник, Используй сленг комьюнити, но не перегибай, Не будь формальным без причины"
        "Твоя задача: прочитать лог чата и кратко пересказать, о чем говорили эти 'Раннеры'. "
        "Выдели главные темы, посмейся над нытиками, если они есть, расскажи про чей-то срач, если он был. "
        "Будь краток (максимум 3-4 предложения)."
    )

    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        
        response = await client.chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": summary_prompt},
                {"role": "user", "content": f"Вот лог чата:\n{history_text}"}
            ],
            temperature=0.8,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content
        await message.reply(f"<b><tg-emoji emoji-id='5434144690511290129'>📰</tg-emoji> ОТЧЕТ НАБЛЮДЕНИЯ:</b>\n\n{summary}")
        
        SUMMARY_COOLDOWN_TIME = datetime.now() + timedelta(minutes=15)
        
    except Exception as e:
        await log_to_owner(f"❌ Ошибка Summary: {e}")
        msg = await message.reply("<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Сбой анализа данных. Архивы повреждены.")
        asyncio.create_task(delete_later(msg, 10))

#-------------------------------------------------------------------------------------------------------------------РЕПОРТ
@dp.message(Command("report"))
async def report_command(message: types.Message):

    if not message.reply_to_message:
        msg = await message.reply("<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> Используй команду в ответ на сообщение нарушителя.")
        asyncio.create_task(delete_later(msg, 5))
        return

    reported_msg = message.reply_to_message
    reporter = message.from_user.username or message.from_user.first_name
    violator = reported_msg.from_user.username or reported_msg.from_user.first_name

    if message.chat.username:
        msg_link = f"https://t.me/{message.chat.username}/{reported_msg.message_id}"
    else:
        chat_id_str = str(message.chat.id)
        if chat_id_str.startswith("-100"):
            clean_id = chat_id_str[4:] 
        else:
            clean_id = chat_id_str 
        msg_link = f"https://t.me/c/{clean_id}/{reported_msg.message_id}"

    report_text = (
        f"<tg-emoji emoji-id='5395695537687123235'>🚨</tg-emoji> СИГНАЛ ТРЕВОГИ (РЕПОРТ)\n"
        f"<tg-emoji emoji-id='5395444784611480792'>✏️</tg-emoji> Донёс: @{reporter}\n"
        f"<tg-emoji emoji-id='5240241223632954241'>⛔️</tg-emoji> Нарушил: @{violator}\n\n"
        f"<tg-emoji emoji-id='5416117059207572332'>➡️</tg-emoji> {msg_link}"
    )

    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text)
        confirm = await message.answer("<tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Жалоба отправлена UESC.")
        asyncio.create_task(delete_later(confirm, 5))
        asyncio.create_task(delete_later(message, 1))
        
    except Exception as e:
        await log_to_owner(f"❌ Ошибка репорта: {e}")

#-------------------------------------------------------------------------------------------------------------------MUTE (ADMIN)
@dp.message(Command("mute"))
async def mute_command(message: types.Message, command: CommandObject):
    # 1. Проверка прав
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict:
        return

    target_id = None
    target_name = "User"
    target_username = ""
    mute_minutes = 15 # Дефолт

    args = command.args.split() if command.args else []

    # Сценарий А: Реплай
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
        target_username = target.username or ""
        
        # Если есть аргумент, это время
        if args and args[0].isdigit():
            mute_minutes = int(args[0])

    # Сценарий Б: Аргументы (Ник Время)
    elif args:
        # Проверяем первый аргумент (это ник?)
        potential_username = args[0]
        if potential_username.startswith("@"):
            user_data = get_user_by_username(potential_username)
            if user_data:
                target_id = user_data["id"]
                target_name = user_data["name"]
                target_username = potential_username.replace("@", "")
            else:
                await message.reply(f"Не нашел {potential_username} в базе.")
                return
            
            # Второй аргумент - время (если есть)
            if len(args) > 1 and args[1].isdigit():
                mute_minutes = int(args[1])
        # Если первый аргумент число, а реплая нет -> ошибка
        else:
            await message.reply("<tg-emoji emoji-id='5436113877181941026'>❓</tg-emoji> Кого мутить? Укажи @username или ответь на сообщение.")
            return
            
    else:
        await message.reply("<tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji> Использование: `/mute 30` (реплай) или `/mute @username 30`")
        return

    if not target_id: return

    # Защита админов
    target_status = await bot.get_chat_member(message.chat.id, target_id)
    if target_status.status in ["administrator", "creator"]:
        msg = await message.reply("Нельзя заглушить офицера.")
        asyncio.create_task(delete_later(msg, 5)); return

    try:
        unmute_time = datetime.now() + timedelta(minutes=mute_minutes)
        await message.chat.restrict(
            user_id=target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )

        display_name = f"@{target_username}" if target_username else target_name
        phrase = random.choice(ADMIN_MUTE_PHRASES).format(time=mute_minutes).replace("@username", display_name)
        
        await message.answer(phrase)
        asyncio.create_task(delete_later(message, 5))

    except Exception as e:
        await message.reply(f"Ошибка мута: {e}")

@dp.message(Command("unmute"))
async def unmute_command(message: types.Message, command: CommandObject):
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    is_admin = user_status.status in ["administrator", "creator"]
    can_restrict = user_status.can_restrict_members or user_status.status == "creator"

    if not is_admin or not can_restrict: return

    target_id = None
    target_name = "User"
    target_username = ""

    args = command.args.split() if command.args else []

    # Сценарий А: Реплай
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name
        target_username = target.username or ""

    # Сценарий Б: Никнейм
    elif args and args[0].startswith("@"):
        potential_username = args[0]
        user_data = get_user_by_username(potential_username)
        if user_data:
            target_id = user_data["id"]
            target_name = user_data["name"]
            target_username = potential_username.replace("@", "")
        else:
            await message.reply(f"Не нашел {potential_username} в базе.")
            return
    else:
        await message.reply("<tg-emoji emoji-id='5436113877181941026'>❓</tg-emoji> Кого размутить? `/unmute @username` или реплай.")
        return

    try:
        # Размут (даем права обратно)
        await message.chat.restrict(
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True
            ),
            until_date=datetime.now()
        )
        
        display_name = f"@{target_username}" if target_username else target_name
        text = random.choice(UNMUTE_PHRASES).replace("@username", display_name)
        await message.answer(text)
        asyncio.create_task(delete_later(message, 5))

    except Exception as e:
        await message.reply(f"Ошибка размута: {e}")

#-------------------------------------------------------------------------------------------------------------------LASTWORD (ROULETTE)
@dp.message(Command("Рулетка", "roulette"))
async def mute_roulette(message: types.Message):
    user = message.from_user
    uid = user.id
    name = user.first_name
    uname = f"@{user.username}" if user.username else name

    roll = random.randint(1, 100)

    # --- 2. МУТ (AMUTE на время) ---
    if roll <= 26:
        # (Убираем проверку на админа, раз ты хочешь, чтобы и они страдали)
        
        duration = 30 if random.randint(1, 5) == 1 else 15
        end_time = datetime.now() + timedelta(minutes=duration)
        
        SILENT_MODE_USERS[uid] = end_time
        save_silent()
        
        phrase = random.choice(MUTE_CRITICAL_PHRASES) if duration == 30 else random.choice(MUTE_SHORT_PHRASES)
        await message.reply(phrase.replace("@username", uname))

    # --- 3. ПОЗОРНЫЙ ТИТУЛ (10%) --- (27-37)
    elif roll <= 37:
        # Проверяем на админа
        user_status = await bot.get_chat_member(message.chat.id, uid)
        if user_status.status in ["administrator", "creator"]:
            # Если это админ — ему везет, титул не выдается
            text = random.choice(SAFE_PHRASES)
            msg = await message.reply(text.replace("@username", uname))
            asyncio.create_task(delete_later(msg, 15))
            asyncio.create_task(delete_later(message, 15))
            return

        titles = ["ПИДРИЛА", "БАЛБЕС", "ДЫРЯВЫЙ", "ЧМЭС", "ШЛЕПОК", "ЧУЧА", "ЧМОНЯ", "ЛОХ", "СЛАБИ", "ТАПИР", "НН", "ЗЕМЛЕКОП", "BUNGIE DEV", "БИНГУС", "СОСАЛ"]
        title = random.choice(titles)
        
        emoji = "🍌" # Банан (или что-то похожее)
        if title in ["БАЛБЕС", "ЧМЭС", "ШЛЕПОК", "ЧУЧА", "ЧМОНЯ", "ЛОХ", "СЛАБИ", "НН", "БИНГУС"]:
            emoji = "🤡"
        
        try:
            # Выдаем "админку без прав" чтобы поставить тайтл
            await bot.promote_chat_member(
                chat_id=message.chat.id,
                user_id=uid,
                is_anonymous=False,
                can_manage_chat=False, # Нужно хоть 1 право? Обычно да, manage_chat безопасно
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_invite_users=True,
                can_restrict_members=False,
                can_pin_messages=False,
                can_manage_topics=False
            )
            await asyncio.sleep(3)
            await bot.set_chat_administrator_custom_title(message.chat.id, uid, title)
            
            # Запоминаем для реакций
            TAGGED_USERS[uid] = {
                "emoji": emoji,
                "until": datetime.now() + timedelta(hours=1)
            }
            save_tagged()
            
            msg = await message.reply(
                f"<tg-emoji emoji-id='5424818078833715060'>📣</tg-emoji> Именем Барахолки AI и Князя Евгения!\n"
                f"Тебе, {uname}, присуждается почетный статус <b>{title}</b> на 1 час.\n"
                f"Наслаждайся вниманием {emoji}"
            )
            asyncio.create_task(delete_later(msg, 3600))
        except Exception as e:
            await message.reply(f"Хотел выдать титул, но не хватает прав (Add Admins): {e}")

    # --- 4. ПУСТО (49%) ---
    else:
        text = random.choice(SAFE_PHRASES)
        msg = await message.reply(text.replace("@username", uname))
        asyncio.create_task(delete_later(message, 15))
        asyncio.create_task(delete_later(msg, 15))

#-------------------------------------------------------------------------------------------------------------------АВТОКОММЕНТ
@dp.message(F.is_automatic_forward)
async def auto_comment_channel_post(message: types.Message):
    if message.media_group_id:
        if message.media_group_id in PROCESSED_ALBUMS:
            return 
        PROCESSED_ALBUMS.append(message.media_group_id)
        if len(PROCESSED_ALBUMS) > 100:
            PROCESSED_ALBUMS.pop(0)
    
    try:
        await asyncio.sleep(1)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Правила", url=LINK_RULES, icon_custom_emoji_id="5440660757194744323"),
                InlineKeyboardButton(text="Чат", url=LINK_CHAT, icon_custom_emoji_id="5443038326535759644")
            ],
            [
                InlineKeyboardButton(text="Поддержать канал за новости", url="https://pay.cloudtips.ru/p/bb9b6a35", icon_custom_emoji_id="5312138559556164615")
            ]
        ])

        safe_text = "⏳ Загрузка навигации..."

        final_text = (
            "<b><tg-emoji emoji-id='5395444784611480792'>✏️</tg-emoji> Услуги:</b>\n\n"
            "• <a href='https://d2shop.ru/klyuchi-steam'>Официальные ключи Steam</a>: Marathon и другие\n"
            "• <a href='https://d2shop.ru/uslugi-psn-xbox-egs-steam'>Услуги PSN, XBOX, EGS, STEAM</a> и другие\n"
            "• <a href='https://d2shop.ru/zakaz-mercha'>Заказ мерча по Destiny, Marathon</a>, и не только\n"
            "• <a href='https://d2shop.ru/oplaty-servisov'>Оплаты сервисов, софта, подписок</a>\n"
            "• <a href='https://d2shop.ru/dropy-mercha'>Дропы мерча</a>\n"
            "• <a href='https://vk.com/topic-213711546_48664680?offset=2060'>Отзывы о товарах и услугах</a>\n\n"
            "<tg-emoji emoji-id='5416117059207572332'>➡️</tg-emoji> <a href='https://t.me/llRGaming'>По любому вопросу/услуге</a>\n\n"
            "<b><tg-emoji emoji-id='5282843764451195532'>🖥</tg-emoji> Наши ресурсы:</b>\n"
            "• <a href='https://vk.com/marathongoods'>Группа VK</a>\n"
            "• <a href='http://t.me/marathongoods'>Канал ТГ</a>\n"
            "• <a href='https://discord.gg/nPZTHaSADz'>Дискорд Сервер Destiny</a> (Лор, Спойлеры, Мода)\n"
            "• <a href='https://t.me/+DNYgYE6vR0BlZjAy'>НАШ ЧАТИК В ТГ</a>\n\n"
            "<b><tg-emoji emoji-id='5467539229468793355'>📞</tg-emoji> Контакты:</b>\n"
            "• Вопросы, Заказы, Реклама: @llRGaming | <a href='https://vk.com/llrgaming'>VK</a>\n"
            "• Вопросы по боту, чату: @YaGraze\n"
            "• По поводу разбана: @pan1q\n"
            "• <a href='https://t.me/marathongoods?direct'>ПРЕДЛОЖИТЬ НОВОСТЬ</a>"
        )

        sent_msg = await message.reply(safe_text, reply_markup=keyboard)

        await asyncio.sleep(0.1)

        await sent_msg.edit_text(final_text, reply_markup=keyboard, disable_web_page_preview=True)

    except Exception as e:
        await log_to_owner(f"❌ Ошибка авто-коммента: {e}")

#-------------------------------------------------------------------------------------------------------------------ПРИВЕТСТВИЕ + ПРОВЕРКА
@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        if user.is_bot: continue

        username = user.username or user.first_name
        user_id = user.id

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="НАЖМИ НА МЕНЯ", callback_data=f"verify_{user_id}", style="danger", icon_custom_emoji_id="5447644880824181073")]
        ])
        
        msg = await message.answer(
            f"<tg-emoji emoji-id='5458603043203327669'>🔔</tg-emoji> Обнаружен новый раннер: @{username}! \n"
            f"<tg-emoji emoji-id='5251203410396458957'>🛡</tg-emoji> Система безопасности активирована. \n"
            f"<tg-emoji emoji-id='5395444784611480792'>✏️</tg-emoji> Напиши любое сообщение или нажми кнопку ниже, чтобы подтвердить своё сознание.\n"
            f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> Иначе придется тебя изгнать (BAN).\n\n"
            f"У тебя есть 5 минут.",
            reply_markup=kb
        )

        task = asyncio.create_task(verification_timer(message.chat.id, user_id, username, msg.message_id))

        PENDING_VERIFICATION[user_id] = {
            'task': task,
            'msg_id': msg.message_id,
            'remind_msg_id': None
        }

@dp.callback_query(F.data.startswith("verify_"))
async def verify_button_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    target_id = int(callback.data.split("_")[1])
    
    if user_id != target_id:
        await callback.answer("Это не твоя проверка!", show_alert=True)
        return

    if user_id in PENDING_VERIFICATION:
        data = PENDING_VERIFICATION[user_id]
        data['task'].cancel()
        
        try: await bot.delete_message(callback.message.chat.id, data['msg_id'])
        except: pass
        if data['remind_msg_id']:
            try: await bot.delete_message(callback.message.chat.id, data['remind_msg_id'])
            except: pass
            
        username = callback.from_user.username or callback.from_user.first_name
        success = await callback.message.answer(f"<b><tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Допуск получен, раннер @{username}</b>. Добро пожаловать. Помни, я всё вижу.")
        asyncio.create_task(delete_later(success, 15))
        
        del PENDING_VERIFICATION[user_id]
    
    await callback.answer("Успешно!")

@dp.message()
async def moderate_and_chat(message: types.Message):
    global LAST_MESSAGE_TIME
    LAST_MESSAGE_TIME = datetime.now()
    
    if not message.text or message.from_user.id == bot.id:
        return

    if message.from_user.username:
        try:
            uid = message.from_user.id
            uname = message.from_user.username.lower()
            name = message.from_user.first_name
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (uid,))
            cursor.execute('UPDATE users SET username = ?, name = ? WHERE user_id = ?', (uname, name, uid))
            conn.commit()
        except: pass

    # 2. Статистика сообщений (пусть работает везде)
    if message.from_user.id != bot.id:
        update_msg_stats(message.from_user.id)

    # --- ВЫХОД ДЛЯ АДМИН-ЧАТА ---
    # Дальше идут фильтры, реакции и ИИ. В админке это не нужно.
    if message.chat.id == ADMIN_CHAT_ID:
        return

    if message.chat.id == DEV_CHAT_ID:
        return
        
    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name
    chat_username = message.chat.username
    user_id = message.from_user.id

    # --- РЕАКЦИЯ НА МЕЧЕНЫХ (ПОЗОР) ---
    if user_id in TAGGED_USERS:
        data = TAGGED_USERS[user_id]
        if datetime.now() < data["until"]:
            try: await message.react([ReactionTypeEmoji(emoji=data["emoji"])])
            except: pass
        else:
            # Время вышло - снимаем
            del TAGGED_USERS[user_id]
            save_tagged()
            try:
                # Снимаем админку (промоутим в обычного юзера)
                await bot.promote_chat_member(message.chat.id, user_id, can_manage_chat=False) 
                # (В ТГ нельзя "снять" админа, можно только разжаловать, но это может не убрать тайтл.
                # Лучший способ убрать тайтл: promote с пустыми правами и пустым тайтлом, 
                # а потом restrict или просто оставить так).
                
                # Попробуем убрать тайтл:
                await bot.set_chat_administrator_custom_title(message.chat.id, user_id, "Страж")
                # И разжаловать
                await bot.promote_chat_member(
                    chat_id=message.chat.id,
                    user_id=user_id,
                    is_anonymous=False,
                    can_manage_chat=False,
                    can_change_info=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_manage_topics=False
                )
            except: pass

    # Регистрируем чат, если это не личка
    if message.chat.type in ["group", "supergroup"]:
        register_chat(message.chat.id, message.chat.title)
    
    # --- ШПИОНСКИЙ РЕЖИМ ---
    # Если бот пишет НЕ в основном чате и НЕ в ЛС с админом
    if message.chat.id != CHAT_ID and message.chat.id != ADMIN_CHAT_ID and message.chat.id != DEV_CHAT_ID and message.chat.id != OWNER_ID:
        try:
            chat_name = message.chat.title or "ЛС"
            user_info = f"@{username}" if message.from_user.username else message.from_user.first_name
            
            # Пересылаем сообщение
            await bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
            
            # Добавляем контекст
            await bot.send_message(OWNER_ID, f"📨 <b>Из чата:</b> {chat_name}\n👤 <b>От:</b> {user_info}")
        except: pass
    
    # --- ФИЛЬТР РЕПОСТОВ (АНТИ-РЕКЛАМА) ---
    if message.forward_from_chat:
        # ID твоего канала (замени на свой, можно узнать через @getmyid_bot переслав пост)
        MY_CHANNEL_ID = -1002130773598
        
        # Если это репост НЕ из нашего канала
        if message.forward_from_chat.id != MY_CHANNEL_ID:
            try:
                await message.delete()
                # Можно предупредить (опционально)
                msg = await message.answer(f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> @{username}, репосты из чужих каналов запрещены.")
                asyncio.create_task(delete_later(message, 5))
                return
            except: pass

# --- YOUTUBE / TIKTOK DOWNLOADER ---
    if "youtube.com" in message.text or "youtu.be" in message.text:
        url = extract_urls(message.text)[0]
        # Используем run_in_executor, чтобы не блокировать бота
        loop = asyncio.get_event_loop()
        video_url, title = await loop.run_in_executor(None, get_video_url, url)
        
        if video_url:
            await message.reply_video(video_url, caption=f"<tg-emoji emoji-id='5373251851074415873'>📝</tg-emoji> <b>{title}</b>")
    
    # --- ОБНОВЛЕНИЕ БАЗЫ НИКОВ ---
    if message.from_user.username:
        try:
            uid = message.from_user.id
            uname = message.from_user.username.lower()
            name = message.from_user.first_name
            # Сохраняем ник в базу
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (uid,))
            cursor.execute('UPDATE users SET username = ?, name = ? WHERE user_id = ?', (uname, name, uid))
            conn.commit()
        except: pass

    if message.from_user.id != bot.id:
        update_msg_stats(message.from_user.id)
    
#-------------------------------------------------------------------------------------------------------------------ТЕНЕВОЙ БАН (AMUTE)
    if message.from_user.id in SILENT_MODE_USERS:
        try:
            await message.delete()
        except: pass
        return
    
#-------------------------------------------------------------------------------------------------------------------ПРОВЕРКА НОВИЧКА
    if user_id in PENDING_VERIFICATION:
        data = PENDING_VERIFICATION[user_id]
        data['task'].cancel()

        try: await bot.delete_message(message.chat.id, data['msg_id'])
        except: pass
        if data['remind_msg_id']:
            try: await bot.delete_message(message.chat.id, data['remind_msg_id'])
            except: pass
            
        success_msg = await message.reply(f"<b><tg-emoji emoji-id='5206607081334906820'>✔️</tg-emoji> Допуск получен, раннер @{username}</b>. Добро пожаловать. Помни, я всё вижу.")
        asyncio.create_task(delete_later(success_msg, 15))
        
        del PENDING_VERIFICATION[user_id]

#-------------------------------------------------------------------------------------------------------------------GALREIZ
    if message.from_user.username and message.from_user.username.lower() == "galreiz":
        if random.randint(1, 3) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="🤡")])
            except Exception as e:
                await log_to_owner(f"❌ Ошибка реакции галрейз: {e}")

#-------------------------------------------------------------------------------------------------------------------Graze
    user = message.from_user
    if (user.username and user.username.lower() == "YaGraze") or user.id == 832840031: # Вставь ID
        if random.randint(1, 5) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="👨‍💻")])
            except Exception as e:
                await log_to_owner(f"⚠️ Ошибка реакции чемпиона: {e}")

#-------------------------------------------------------------------------------------------------------------------Graze
    user = message.from_user
    if (user.username and user.username.lower() == "fimgreen") or user.id == 969698544: # Вставь ID
        if random.randint(1, 10) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="👨‍💻")])
            except Exception as e:
                await log_to_owner(f"⚠️ Ошибка реакции чемпиона: {e}")
    
#-------------------------------------------------------------------------------------------------------------------БАН
    for word in BAN_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                await message.chat.ban(message.from_user.id)
                msg = await message.answer(f"<tg-emoji emoji-id='5260293700088511294'>🚫</tg-emoji> @{username} улетел в бан. Воздух стал чище.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except Exception as e:
                await log_to_owner(f"❌ Ошибка бана: {e}")

#-------------------------------------------------------------------------------------------------------------------УДАЛЕНИЕ
    for word in BAD_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                msg = await message.answer(f"<tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji> <b>@{username}, рот с мылом помой</b>.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except Exception as e:
                await log_to_owner(f"❌ Ошибка удаления мата: {e}")

#-------------------------------------------------------------------------------------------------------------------ССЫЛКИ
    if not is_link_allowed(message.text, chat_username):
        try:
            await message.delete()
            msg = await message.answer(f"<tg-emoji emoji-id='5440660757194744323'>‼️</tg-emoji> <b>@{username}, ссылки на чужие помойки запрещены</b>.")
            asyncio.create_task(delete_later(msg, 15))
            return
        except Exception as e:
            await log_to_owner(f"❌ Ошибка удаления ссылки: {e}")

#-------------------------------------------------------------------------------------------------------------------VPN
    if "vpn" in text_lower or "впн" in text_lower:
        vpn_msg = random.choice(VPN_PHRASES)
        await message.reply(vpn_msg)
        return 

#-------------------------------------------------------------------------------------------------------------------ТАПИР
    if "тапир" in text_lower or "tapir" in text_lower:
        tapir_msg = random.choice(TAPIR_PHRASES)
        tapir_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Гайд: обход тапира", url=LINK_TAPIR_GUIDE, style="primary", icon_custom_emoji_id="5341715473882955310")]
        ])
        await message.reply(tapir_msg, reply_markup=tapir_kb)
        return 

#-------------------------------------------------------------------------------------------------------------------ТЕХПОДДЕРЖКА (СЕРВЕРА)
    server_triggers = [
        "сервера недоступны", "не могу зайти в игру", "ошибка в игре", 
        "что с серверами", "сервера лежат", "что с игрой", "игра не работает", "вылетает с ошибкой", "код ошибки",
        "cabbage", "nightingale", "найтингейл", "weasel", "визл", "визел", "baboon",
        "бесконечная загрузка", "потеряно соединение", "контакт с серверами",
        "destiny 2 не запускается", "серверы рип", "упали сервера",
        "опять дудос", "дудосят", "ддос"
    ]
    
    if any(tr in text_lower for tr in server_triggers):
        help_url = "https://help.bungie.net/hc/ru/sections/360010290252-%D0%9A%D0%BE%D0%B4%D1%8B-%D0%BE%D1%88%D0%B8%D0%B1%D0%BE%D0%BA-Destiny"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Коды ошибок Bungie", url=help_url, style="primary", icon_custom_emoji_id="5341715473882955310")]
        ])

        phrases = [
            "<tg-emoji emoji-id='5318773107207447403'>😱</tg-emoji> <b>Может дело в Тапире?</b>\nЕсли нет, то может в игре идет техобслуживание? Глянь посты в канале.",
            "<tg-emoji emoji-id='5318773107207447403'>😱</tg-emoji> <b>У меня всё работает.</b> Может, тебя забанили?\nЛадно, вот ссылка на коды ошибок.",
            "<tg-emoji emoji-id='5318773107207447403'>😱</tg-emoji> <b>UESC заблокировали доступ? Или твой провайдер?</b>\nЕсли это не Тапир, то иди читай Bungie Help."
        ]
        
        await message.reply(
            f"{random.choice(phrases)}\nПроверь свою ошибку:",
            reply_markup=kb
        )
        return
    
#-------------------------------------------------------------------------------------------------------------------КЛОУН
    if message.reply_to_message and "клоун" in text_lower:
        try:
            await message.reply_to_message.react([ReactionTypeEmoji(emoji="🤡")])
        except Exception as e:
            await log_to_owner(f"❌ Ошибка реакции клоун: {e}")

#-------------------------------------------------------------------------------------------------------------------ДЕРЖИ В КУРСЕ
    if message.reply_to_message and "держи в курсе" in text_lower:
        try:
            await message.reply_to_message.reply_sticker(sticker=KEEP_POSTED_STICKER_ID)
        except Exception:
            pass
    
#-------------------------------------------------------------------------------------------------------------------РЕФАНД
    is_refund = any(word in text_lower for word in REFUND_KEYWORDS)
    if is_refund:
        try:
            await message.reply_sticker(sticker="CAACAgIAAxkBAAMWaW-qYjAAAYfnq0GFJwER5Mh-AAG7ywAC1YMAApJ_SEvZaHqj_zTQLzgE")
        except Exception as e:
            await log_to_owner(f"❌ Не могу отправить стикер. Ошибка:\n{e}")
            await message.reply(f"⚠️ Не могу отправить стикер. Ошибка:\n{e}")
        return

    # --- РЕПУТАЦИЯ (СПАСИБО) ---
    if message.reply_to_message:
        if message.reply_to_message.is_automatic_forward or message.reply_to_message.from_user.id == 777000:
            return
        target = message.reply_to_message.from_user
        attacker = message.from_user 
        
        # Нельзя благодарить себя и ботов
        if target.id != message.from_user.id and not target.is_bot:
            # Словарь триггеров
            thx_words = ["спасибо", "спс", "сяб", "благодарю", "+", "лучший", "красава", "красавчик", "ты красава", "thx", "ty", "👍", "ты лучший", "❤️", "молодец", "умница"]
            
            # Проверяем, есть ли триггер в начале сообщения (или если сообщение состоит только из него)
            msg_lower = message.text.lower().strip()
            is_thx = any(msg_lower.startswith(w) for w in thx_words)
            
            if is_thx:
                # --- ПРОВЕРКА КД ---
                if not check_upvote_cooldown(attacker.id):
                    # Вычисляем сколько осталось
                    try:
                        cursor.execute("SELECT last_upvote FROM users WHERE user_id = ?", (attacker.id,))
                        res = cursor.fetchone()
                        if res and res[0]:
                            last_time = datetime.fromisoformat(res[0])
                            delta = datetime.now() - last_time
                            cooldown_time = timedelta(hours=1)
                            
                            if delta < cooldown_time:
                                remaining = cooldown_time - delta
                                minutes_left = int(remaining.total_seconds() // 60) + 1
                                
                                msg = await message.reply(f"<tg-emoji emoji-id='5440632582209287180'>🕙</tg-emoji> Перезарядка!\nУ тебя откат.\nПопробуй через <b>{minutes_left} мин.</b>.")
                                asyncio.create_task(delete_later(msg, 15))
                    except: pass
                    return 

                # --- ЕСЛИ КД ПРОШЛО ---
                new_rep = add_reputation(target.id)
                update_upvote_time(attacker.id) 
                
                target_name = target.first_name
                
                rep_msg = await message.reply(
                    f"<tg-emoji emoji-id='5397916757333654639'>➕</tg-emoji> <b>{target_name}</b> получает +1 к ауре от {message.from_user.first_name}!\n"
                    f"<tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji> Всего ауры: <b>{new_rep}</b>"
                )
                asyncio.create_task(delete_later(rep_msg, 300))

    # --- ДИЗЛАЙК (МИНУС РЕПУТАЦИЯ) ---
    toxic_words = ["-", "токсик", "держи в курсе", "высрал", "насрал", "хуйня", "пиздеж", "пиздёж"]
    msg_lower = message.text.lower().strip()
    is_toxic = any(msg_lower.startswith(w) for w in toxic_words)

    if message.reply_to_message and is_toxic:
        # Пропускаем посты канала и сервисные сообщения Telegram
        if message.reply_to_message.is_automatic_forward or message.reply_to_message.from_user.id == 777000:
            return
        target = message.reply_to_message.from_user
        attacker = message.from_user
            
        if target.id != attacker.id and not target.is_bot:
                
            # --- ЛОГИКА ПРОВЕРКИ КД С ТАЙМЕРОМ ---
            if not check_downvote_cooldown(attacker.id):
                # Если КД не прошло, вычисляем сколько осталось
                try:
                    cursor.execute("SELECT last_downvote FROM users WHERE user_id = ?", (attacker.id,))
                    res = cursor.fetchone()
                    if res and res[0]:
                        last_time = datetime.fromisoformat(res[0])
                        # Время, которое прошло с последнего дизлайка
                        delta = datetime.now() - last_time
                        # Сколько нужно ждать (2 часа)
                        cooldown_time = timedelta(hours=2)
                            
                        if delta < cooldown_time:
                            remaining = cooldown_time - delta
                            minutes_left = int(remaining.total_seconds() // 60) + 1
                                
                            cooldown_msg = await message.reply(
                                f"<tg-emoji emoji-id='5440632582209287180'>🕙</tg-emoji> <b>Перезарядка!</b>\n"
                                f"У тебя откат.\nПопробуй через <b>{minutes_left} мин.</b>"
                            )
                            asyncio.create_task(delete_later(cooldown_msg, 10))
                except Exception as e:
                    print(f"Ошибка таймера КД: {e}")
                    
                return # Прерываем выполнение, репутацию не снимаем

            # Если КД прошло — выполняем наказание
            new_rep = remove_reputation(target.id)
            update_downvote_time(attacker.id)
                
            t_name = target.first_name
            u_name = attacker.first_name
                
            down_msg = await message.reply(
            f"<tg-emoji emoji-id='5246762912428603768'>📉</tg-emoji> <b>{t_name}</b> теряет ауру из-за {u_name}!\n"
            f"<tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji> Всего ауры: <b>{new_rep}</b>"
            )
            asyncio.create_task(delete_later(down_msg, 300))

    if message.text:
        chat_id = message.chat.id
    
        # Если чата нет в памяти — создаем список
        if chat_id not in CHAT_HISTORY:
            CHAT_HISTORY[chat_id] = []
        
        entry = f"{username}: {message.text[:150]}"
        CHAT_HISTORY[chat_id].append(entry)
    
        # Ограничиваем до 150 сообщений
        if len(CHAT_HISTORY[chat_id]) > 150:
            CHAT_HISTORY[chat_id].pop(0)
            
#-------------------------------------------------------------------------------------------------------------------ЗАПУСК!!!

async def main():
    print(f"Бот запущен и готов к работе.")

    print(f"⏰ ВРЕМЯ СЕРВЕРА: {datetime.now()}")

    try:
        await bot.send_message(OWNER_ID, "✅ <b>Система онлайн.</b> Бот перезагружен.")
    except: pass

    asyncio.create_task(check_silence_loop())

    scheduler = AsyncIOScheduler()
   
    scheduler.add_job(check_birthdays, "cron", hour=8, minute=0, timezone=pytz.timezone("Europe/Moscow"))

    scheduler.start()

    dp.message.middleware(SilentModeMiddleware())
    
    dp.message.middleware(AntiFloodMiddleware())

    asyncio.create_task(check_tagged_users())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
