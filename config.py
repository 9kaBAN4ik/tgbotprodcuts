# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
TOKEN = os.getenv("BOT_TOKEN")  # Токен бота
DB_PATH = os.getenv("DB_PATH", "data/database.db")  # Путь к базе данных, по умолчанию data/database.db

# Настройки для реферальной системы
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", 10))  # Награда за реферала (по умолчанию 10 VED)
CURRENCY = os.getenv("CURRENCY", "VED")  # Внутренняя валюта

# Языковые настройки
LANGUAGES = ["ru", "en"]  # Доступные языки
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru")  # Язык по умолчанию

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # Уровень логирования по умолчанию INFO

# Настройки для платежей
PAYMENT_CURRENCY = {
    "BTC": os.getenv("BTC_RATE", "0.000058849008"),  # Курс BTC к VED
    "USDT": os.getenv("USDT_RATE", "1.12"),          # Курс USDT к VED
    "YooMoney": os.getenv("YOOMONEY_RATE", "1.0")    # Пример ставки для YooMoney
}

api_secret = "blckjvodnlwekjvdvlfvkbskbsdlvbfkdvhdflvbdfjvbfv"
BTCAddr = "1SxybDn1P64qqCb75vrgxQpj8zDFeSzDp"
# Прочие настройки (если нужны дополнительные параметры)
ADMIN_ID = 2025904026
