#!/usr/bin/env python3
"""
Simple configuration for FantasyPros analytics
"""
import os
from typing import Optional

class Config:
    """Simple app configuration"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL', 
        'postgresql://postgres:password@localhost:5432/fantasypros'
    )
    
    # App settings
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT: int = int(os.getenv('PORT', '8000'))
    
    # Scraping
    SCRAPING_DELAY: float = float(os.getenv('SCRAPING_DELAY', '1.0'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    
    # Current season
    CURRENT_YEAR: int = int(os.getenv('CURRENT_YEAR', '2025'))
    
    @classmethod
    def get_current_week(cls) -> int:
        """Get current NFL week (0 = draft season)"""
        from datetime import datetime
        now = datetime.now()
        
        # Simple logic: July-August = draft (week 0), Sept+ = regular season
        if now.month in [7, 8]:
            return 0
        elif now.month >= 9:
            # Rough approximation of NFL weeks
            week = ((now - datetime(now.year, 9, 1)).days // 7) + 1
            return min(max(week, 1), 18)
        else:
            return 0

config = Config() 