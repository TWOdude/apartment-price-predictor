"""Data processing and feature engineering."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple

from scraper.utils import setup_logger

logger = setup_logger()


class DataProcessor:
    """Process and prepare apartment data for modeling."""
    
    def __init__(self, raw_data_path: Path):
        """Initialize processor.
        
        Args:
            raw_data_path: Path to raw CSV file
        """
        self.raw_data_path = raw_data_path
        self.df = None
        self.logger = logger
    
    def load_data(self) -> pd.DataFrame:
        """Load raw data from CSV.
        
        Returns:
            Loaded DataFrame
        """
        try:
            self.df = pd.read_csv(self.raw_data_path)
            self.logger.info(f"Loaded {len(self.df)} records from {self.raw_data_path}")
            return self.df
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def clean_data(self) -> pd.DataFrame:
        """Clean and remove invalid records.
        
        Returns:
            Cleaned DataFrame
        """
        if self.df is None:
            self.load_data()
        
        initial_rows = len(self.df)
        
        # Remove duplicates
        self.df = self.df.drop_duplicates(subset=['url'], keep='first')
        
        # Remove records with missing critical values
        self.df = self.df.dropna(subset=['price', 'area', 'rooms'])
        
        # Remove outliers (price and area)
        self.df = self._remove_outliers()
        
        removed = initial_rows - len(self.df)
        self.logger.info(f"Cleaned data: removed {removed} invalid records")
        
        return self.df
    
    def _remove_outliers(self) -> pd.DataFrame:
        """Remove statistical outliers.
        
        Returns:
            DataFrame without outliers
        """
        df = self.df.copy()
        
        # Price outliers (IQR method)
        Q1_price = df['price'].quantile(0.25)
        Q3_price = df['price'].quantile(0.75)
        IQR_price = Q3_price - Q1_price
        
        df = df[
            (df['price'] >= Q1_price - 1.5 * IQR_price) &
            (df['price'] <= Q3_price + 1.5 * IQR_price)
        ]
        
        # Area outliers
        Q1_area = df['area'].quantile(0.25)
        Q3_area = df['area'].quantile(0.75)
        IQR_area = Q3_area - Q1_area
        
        df = df[
            (df['area'] >= Q1_area - 1.5 * IQR_area) &
            (df['area'] <= Q3_area + 1.5 * IQR_area)
        ]
        
        return df
    
    def feature_engineering(self) -> pd.DataFrame:
        """Create new features for modeling.
        
        Returns:
            DataFrame with engineered features
        """
        if self.df is None:
            self.load_data()
        
        # Price per square meter
        self.df['price_per_sqm'] = self.df['price'] / self.df['area']
        
        # Room size (average square meters per room)
        self.df['room_size'] = self.df['area'] / self.df['rooms']
        
        # Features from floor
        if 'floor' in self.df.columns:
            self.df['is_first_floor'] = (self.df['floor'] == 1).astype(int)
            self.df['is_last_floor'] = (self.df['floor'] == self.df['total_floors']).astype(int)
        
        # Features from year (if available)
        if 'year_built' in self.df.columns:
            current_year = 2026
            self.df['building_age'] = current_year - self.df['year_built']
        
        self.logger.info("Feature engineering completed")
        return self.df
    
    def prepare_for_training(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for model training.
        
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        if self.df is None:
            self.load_data()
        
        self.clean_data()
        self.feature_engineering()
        
        # Separate target and features
        X = self.df.drop('price', axis=1)
        y = self.df['price']
        
        # Select only numeric features
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X = X[numeric_cols]
        
        self.logger.info(f"Data prepared for training: {X.shape[0]} samples, {X.shape[1]} features")
        
        return X, y
    
    def save_processed_data(self, output_path: Path) -> None:
        """Save processed data to CSV.
        
        Args:
            output_path: Path to save CSV
        """
        if self.df is None:
            self.logger.error("No data to save")
            return
        
        try:
            self.df.to_csv(output_path, index=False)
            self.logger.info(f"Processed data saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving processed data: {e}")
            raise
