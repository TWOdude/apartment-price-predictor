"""Utility functions for scraping and data processing."""

import time
import random
from typing import Optional
from pathlib import Path
import csv

from loguru import logger
from scraper.config import LOG_FILE

# Configure logger
logger.add(LOG_FILE, rotation="500 MB", level="INFO")


def setup_logger():
    """Setup logger configuration."""
    return logger


def random_delay(min_delay: float, max_delay: float) -> None:
    """Add random delay between min and max seconds.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def save_to_csv(data: list, filepath: Path, mode: str = 'w') -> None:
    """Save data to CSV file.
    
    Args:
        data: List of dictionaries with apartment data
        filepath: Path to CSV file
        mode: Write mode ('w' for new, 'a' for append)
    """
    if not data:
        logger.warning("No data to save")
        return
    
    try:
        keys = data[0].keys()
        
        with open(filepath, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            
            # Write header only for new files
            if mode == 'w':
                writer.writeheader()
            
            writer.writerows(data)
        
        logger.info(f"Saved {len(data)} records to {filepath}")
    
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        raise


def load_from_csv(filepath: Path) -> list:
    """Load data from CSV file.
    
    Args:
        filepath: Path to CSV file
    
    Returns:
        List of dictionaries
    """
    try:
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        logger.info(f"Loaded {len(data)} records from {filepath}")
        return data
    
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return []
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []


def clean_price(price_str: str) -> Optional[int]:
    """Extract numeric price from string.
    
    Args:
        price_str: Price string (e.g., "5 500 000 ₽")
    
    Returns:
        Integer price or None
    """
    try:
        # Remove currency symbols and spaces
        cleaned = price_str.replace('₽', '').replace(' ', '').strip()
        return int(cleaned)
    except (ValueError, AttributeError):
        return None


def clean_area(area_str: str) -> Optional[float]:
    """Extract numeric area from string.
    
    Args:
        area_str: Area string (e.g., "42.5 м²")
    
    Returns:
        Float area or None
    """
    try:
        # Remove 'м²' and spaces
        cleaned = area_str.replace('м²', '').replace(',', '.').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def clean_rooms(rooms_str: str) -> Optional[int]:
    """Extract number of rooms from string.
    
    Args:
        rooms_str: Rooms string (e.g., "2-к", "студия")
    
    Returns:
        Integer rooms or None
    """
    try:
        if "студия" in rooms_str.lower():
            return 1
        # Extract number before '-к'
        cleaned = rooms_str.replace('-к', '').strip()
        return int(cleaned)
    except (ValueError, AttributeError):
        return None


def clean_floor(floor_str: str) -> Optional[int]:
    """Extract floor number from string.
    
    Args:
        floor_str: Floor string (e.g., "3 из 5")
    
    Returns:
        Integer floor or None
    """
    try:
        # Extract first number
        floor_num = floor_str.split()[0]
        return int(floor_num)
    except (ValueError, AttributeError, IndexError):
        return None


def clean_year(year_str: str) -> Optional[int]:
    """Extract year from string.
    
    Args:
        year_str: Year string (e.g., "2015")
    
    Returns:
        Integer year or None
    """
    try:
        year = int(year_str)
        if 1800 <= year <= 2100:
            return year
        return None
    except (ValueError, AttributeError):
        return None
