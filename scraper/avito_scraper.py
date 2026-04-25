"""Avito apartment scraper for collecting data."""

import time
from typing import List, Dict, Optional
from urllib.parse import urljoin
import json

import requests
from bs4 import BeautifulSoup

from scraper.config import (
    AVITO_SPB_URL,
    DEFAULT_HEADERS,
    DELAY_BETWEEN_REQUESTS,
    DELAY_BETWEEN_PAGES,
    TARGET_LISTINGS,
    LISTINGS_PER_PAGE,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    OUTPUT_FILE,
    FEATURES_TO_EXTRACT,
)
from scraper.utils import setup_logger, random_delay, save_to_csv, clean_price, clean_area, clean_rooms, clean_floor, clean_year

logger = setup_logger()


class AvitoScraper:
    """Scraper for Avito.ru apartment listings."""
    
    def __init__(self):
        """Initialize scraper."""
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.listings = []
        self.base_url = AVITO_SPB_URL
        self.logger = logger
    
    def fetch_page(self, url: str, retries: int = 0) -> Optional[BeautifulSoup]:
        """Fetch and parse a single page.
        
        Args:
            url: URL to fetch
            retries: Current retry attempt
        
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'html.parser')
        
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                self.logger.warning(f"Error fetching {url}, retrying... ({retries + 1}/{MAX_RETRIES})")
                random_delay(5, 10)
                return self.fetch_page(url, retries + 1)
            else:
                self.logger.error(f"Failed to fetch {url} after {MAX_RETRIES} retries: {e}")
                return None
    
    def extract_listings_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract apartment listings from page.
        
        Args:
            soup: BeautifulSoup object
        
        Returns:
            List of apartment dictionaries
        """
        listings = []
        
        try:
            # Find all listing items
            # Note: Avito's HTML structure changes frequently, adjust selectors as needed
            items = soup.find_all('div', {'data-item-id': True})
            
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
            
            # Extract item ID and URL
            item_id = item.get('data-item-id')
            url_element = item.find('a', {'class': 'title-root'})
            
            if url_element and url_element.get('href'):
                listing['url'] = urljoin(self.base_url, url_element['href'])
                listing['item_id'] = item_id
            else:
                return None
            
            # Extract title (contains rooms, area info)
            title_element = item.find('h3', {'class': 'title-root'})
            if title_element:
                listing['title'] = title_element.get_text(strip=True)
            
            # Extract price
            price_element = item.find('span', {'class': 'price-text'})
            if price_element:
                price_text = price_element.get_text(strip=True)
                listing['price'] = clean_price(price_text)
            
            # Extract location/district
            location_element = item.find('div', {'class': 'geo'})
            if location_element:
                listing['district'] = location_element.get_text(strip=True)
            
            # Extract additional info (area, rooms, etc.)
            info_elements = item.find_all('div', {'class': 'info-row'})
            for info in info_elements:
                text = info.get_text(strip=True)
                
                if 'м²' in text:
                    listing['area'] = clean_area(text)
                elif '-к' in text or 'студия' in text:
                    listing['rooms'] = clean_rooms(text)
            
            # Extract date
            date_element = item.find('div', {'class': 'date'})
            if date_element:
                listing['posted_date'] = date_element.get_text(strip=True)
            
            return listing if listing.get('price') else None
        
        except Exception as e:
            self.logger.warning(f"Error parsing listing item: {e}")
            return None
    
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
        
        while len(self.listings) < TARGET_LISTINGS and page <= max_pages:
            try:
                url = self.get_next_page_url(page)
                soup = self.fetch_page(url)
                
                if not soup:
                    self.logger.warning(f"Failed to fetch page {page}, stopping")
                    break
                
                page_listings = self.extract_listings_from_page(soup)
                self.listings.extend(page_listings)
                
                self.logger.info(f"Page {page}: collected {len(page_listings)} listings (total: {len(self.listings)})")
                
                if len(self.listings) < TARGET_LISTINGS:
                    random_delay(DELAY_BETWEEN_PAGES, DELAY_BETWEEN_PAGES + 3)
                
                page += 1
            
            except Exception as e:
                self.logger.error(f"Error on page {page}: {e}")
                page += 1
                continue
        
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
