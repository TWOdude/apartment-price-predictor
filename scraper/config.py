"""Configuration for Avito scraper."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Create directories if they don't exist
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Avito base URL
AVITO_BASE_URL = "https://www.avito.ru"
AVITO_SPB_URL = "https://www.avito.ru/sankt-peterburg/kvartiry/prodam"

# Search parameters
CITY = "Санкт-Петербург"
APARTMENT_TYPE = "квартиры"
OFFER_TYPE = "prodam"  # продам

# Scraping settings
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Delays (in seconds) to avoid being blocked
DELAY_BETWEEN_REQUESTS = 2  # Задержка между запросами
DELAY_BETWEEN_PAGES = 3     # Задержка между страницами

# Number of listings to scrape
TARGET_LISTINGS = 5000
LISTINGS_PER_PAGE = 50  # Авито показывает 50 объявлений на странице

# Features to extract
FEATURES_TO_EXTRACT = [
    "price",           # Цена
    "area",            # Площадь (м²)
    "rooms",           # Количество комнат
    "floor",           # Этаж
    "total_floors",    # Всего этажей
    "year_built",      # Год постройки
    "district",        # Район
    "address",         # Адрес
    "description",     # Описание
    "url",             # URL объявления
    "seller_type",     # Тип продавца (физ.лицо, агентство)
    "posted_date",     # Дата публикации
]

# Output file
OUTPUT_FILE = DATA_RAW_DIR / f"{CITY.lower().replace(' ', '_')}_apartments.csv"

# Logging
LOG_FILE = PROJECT_ROOT / "logs" / "scraper.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Timeout for requests
REQUEST_TIMEOUT = 10

# Maximum retries
MAX_RETRIES = 3
