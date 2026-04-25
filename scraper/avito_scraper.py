"""Avito apartment scraper using Selenium for dynamic content loading."""

import time
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from scraper.config import (
    AVITO_SPB_URL,
    DELAY_BETWEEN_REQUESTS,
    DELAY_BETWEEN_PAGES,
    TARGET_LISTINGS,
    LISTINGS_PER_PAGE,
    OUTPUT_FILE,
)
from scraper.utils import setup_logger, random_delay, save_to_csv, clean_price, clean_area, clean_rooms, clean_floor, clean_year

logger = setup_logger()


class AvitoScraper:
    """Scraper for Avito.ru apartment listings using Selenium."""
    
    def __init__(self):
        """Initialize scraper with Selenium WebDriver."""
        self.listings = []
        self.base_url = AVITO_SPB_URL
        self.logger = logger
        self.driver = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        try:
            options = webdriver.ChromeOptions()
            # Убираем headless чтобы видеть что происходит (можно включить позже)
            # options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Автоматическая установка ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing WebDriver: {e}")
            self.logger.info("Installing ChromeDriver automatically...")
            raise
    
    def fetch_page(self, url: str, wait_time: int = 10) -> bool:
        """Fetch page using Selenium and wait for content to load.
        
        Args:
            url: URL to fetch
            wait_time: Maximum time to wait for content (seconds)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Loading page: {url}")
            self.driver.get(url)
            
            # Ждём, пока элементы загрузятся
            # Ищем контейнер со списком объявлений
            wait = WebDriverWait(self.driver, wait_time)
            
            # Пытаемся найти список объявлений
            # Авито использует разные селекторы, пробуем несколько
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-item-id]")))
                self.logger.info("Items found on page")
            except TimeoutException:
                self.logger.warning("Timeout waiting for items, continuing anyway...")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error fetching page {url}: {e}")
            return False
    
    def extract_listings_from_page(self) -> List[Dict]:
        """Extract apartment listings from loaded page.
        
        Returns:
            List of apartment dictionaries
        """
        listings = []
        
        try:
            # Даём странице время на полную загрузку
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Ищем элементы с data-item-id атрибутом
            items = soup.find_all(attrs={'data-item-id': True})
            
            self.logger.info(f"Found {len(items)} items on page")
            
            for item in items:
                try:
                    listing = self._parse_listing(item)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    self.logger.warning(f"Error parsing listing: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error extracting listings: {e}")
        
        return listings
    
    def _parse_listing(self, item) -> Optional[Dict]:
        """Parse single listing item.
        
        Args:
            item: BeautifulSoup element
        
        Returns:
            Dictionary with listing data or None
        """
        try:
            listing = {}
            
            # Получаем item_id
            item_id = item.get('data-item-id')
            if not item_id:
                return None
            
            listing['item_id'] = item_id
            
            # Ищем ссылку на объявление
            link = item.find('a', href=True)
            if link:
                url = link.get('href', '')
                listing['url'] = urljoin(self.base_url, url) if not url.startswith('http') else url
            else:
                return None
            
            # Получаем текст элемента для парсинга
            text = item.get_text(strip=True)
            
            # Ищем цену - обычно это число с пробелами и ₽
            price_match = re.search(r'(\d[\d\s]+)\s*₽', text)
            if price_match:
                price_text = price_match.group(1).replace(' ', '')
                try:
                    listing['price'] = int(price_text)
                except ValueError:
                    listing['price'] = None
            else:
                # Объявление может быть без цены
                listing['price'] = None
            
            # Ищем площадь (м²)
            area_match = re.search(r'(\d+[.,]\d*|\d+)\s*м²', text)
            if area_match:
                area_text = area_match.group(1).replace(',', '.')
                try:
                    listing['area'] = float(area_text)
                except ValueError:
                    listing['area'] = None
            else:
                listing['area'] = None
            
            # Ищем количество комнат
            # Ищем паттерны типа "1-к", "2-к", "студия"
            if 'студия' in text.lower():
                listing['rooms'] = 1
            else:
                rooms_match = re.search(r'(\d+)\s*-?к', text)
                if rooms_match:
                    try:
                        listing['rooms'] = int(rooms_match.group(1))
                    except ValueError:
                        listing['rooms'] = None
                else:
                    listing['rooms'] = None
            
            # Ищем этаж
            floor_match = re.search(r'(\d+)\s*[из/]\s*(\d+)', text)
            if floor_match:
                try:
                    listing['floor'] = int(floor_match.group(1))
                    listing['total_floors'] = int(floor_match.group(2))
                except ValueError:
                    listing['floor'] = None
                    listing['total_floors'] = None
            else:
                listing['floor'] = None
                listing['total_floors'] = None
            
            # Ищем название/заголовок
            title = item.find(['h1', 'h2', 'h3', 'span', 'div'], class_=re.compile('title|name|heading'))
            if title:
                listing['title'] = title.get_text(strip=True)
            else:
                listing['title'] = text[:100]
            
            # Район (обычно последняя часть текста)
            listing['district'] = None
            
            # Вернуть только если есть хоть какие-то данные
            if listing.get('price'):
                return listing
            
            return None
        
        except Exception as e:
            self.logger.warning(f"Error parsing listing item: {e}")
            return None
    
    def scroll_page(self):
        """Scroll page to load more items dynamically."""
        try:
            # Скроллим страницу вниз несколько раз
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                time.sleep(1)
            self.logger.info("Page scrolled")
        except Exception as e:
            self.logger.warning(f"Error scrolling page: {e}")
    
    def get_next_page_url(self, current_page: int) -> str:
        """Generate URL for next page.
        
        Args:
            current_page: Current page number
        
        Returns:
            URL for next page
        """
        return f"{self.base_url}?p={current_page}"
    
    def scrape(self) -> List[Dict]:
        """Main scraping method.
        
        Returns:
            List of all collected listings
        """
        self.logger.info(f"Starting scrape: Target {TARGET_LISTINGS} listings")
        self.listings = []
        
        page = 1
        max_pages = (TARGET_LISTINGS // LISTINGS_PER_PAGE) + 2
        
        try:
            while len(self.listings) < TARGET_LISTINGS and page <= max_pages:
                try:
                    url = self.get_next_page_url(page)
                    
                    if not self.fetch_page(url):
                        self.logger.warning(f"Failed to fetch page {page}, stopping")
                        break
                    
                    # Скроллим для загрузки дополнительных элементов
                    self.scroll_page()
                    
                    page_listings = self.extract_listings_from_page()
                    self.listings.extend(page_listings)
                    
                    self.logger.info(f"Page {page}: collected {len(page_listings)} listings (total: {len(self.listings)})")
                    
                    if len(self.listings) < TARGET_LISTINGS and page < max_pages:
                        random_delay(DELAY_BETWEEN_PAGES, DELAY_BETWEEN_PAGES + 3)
                    
                    page += 1
                
                except Exception as e:
                    self.logger.error(f"Error on page {page}: {e}")
                    page += 1
                    continue
        
        finally:
            self.close()
        
        self.logger.info(f"Scraping completed. Total listings: {len(self.listings)}")
        return self.listings
    
    def save_results(self, filepath=None) -> None:
        """Save scraped data to CSV.
        
        Args:
            filepath: Output file path (default from config)
        """
        if filepath is None:
            filepath = OUTPUT_FILE
        
        save_to_csv(self.listings, filepath)
        self.logger.info(f"Data saved to {filepath}")
    
    def close(self):
        """Close WebDriver."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")
        except Exception as e:
            self.logger.warning(f"Error closing WebDriver: {e}")


def main():
    """Main function to run scraper."""
    try:
        scraper = AvitoScraper()
        listings = scraper.scrape()
        scraper.save_results()
        
        logger.info(f"✓ Successfully scraped {len(listings)} apartments")
        return listings
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
