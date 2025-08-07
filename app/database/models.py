#!/usr/bin/env python3
"""
Simple database models for FantasyPros analytics
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class Player(Base):
    """Player information"""
    __tablename__ = 'players'
    
    id = Column(String, primary_key=True)  # fantasypros player ID
    name = Column(String, nullable=False, index=True)
    position = Column(String, nullable=False, index=True)  # QB, RB, WR, TE, K, DST
    team = Column(String, nullable=True, index=True)
    bye_week = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_player_position_team', 'position', 'team'),
    )

class Ranking(Base):
    """Player rankings"""
    __tablename__ = 'rankings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Player info
    player_id = Column(String, nullable=False, index=True)
    player_name = Column(String, nullable=False)  # Denormalized for easy queries
    position = Column(String, nullable=False, index=True)
    team = Column(String, nullable=True)
    
    # Ranking details
    year = Column(Integer, nullable=False, index=True)
    week = Column(Integer, nullable=False, index=True)  # 0 = draft
    scoring = Column(String, nullable=False, index=True)  # STD, PPR, HALF
    
    # Ranking data
    rank_ecr = Column(Integer, nullable=True, index=True)
    rank_min = Column(Integer, nullable=True)
    rank_max = Column(Integer, nullable=True)
    rank_avg = Column(Float, nullable=True)
    rank_std = Column(Float, nullable=True, index=True)  # For tier generation
    adp = Column(Integer, nullable=True)
    
    # Generated tier (filled by analytics)
    tier = Column(Integer, nullable=True, index=True)
    
    # Timestamp
    scraped_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        # Prevent duplicate rankings
        Index('idx_unique_ranking', 'player_id', 'year', 'week', 'scoring', unique=True),
        # Common query patterns
        Index('idx_ranking_position_week', 'position', 'week', 'year'),
        Index('idx_ranking_tier', 'tier', 'position'),
        Index('idx_ranking_std', 'rank_std'),
    )

class ScrapingLog(Base):
    """Simple logging for scraping jobs"""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job details
    position = Column(String, nullable=False)
    scoring = Column(String, nullable=False)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    
    # Results
    success = Column(Boolean, nullable=False)
    players_scraped = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_scraping_log_date', 'started_at'),
        Index('idx_scraping_log_success', 'success'),
    )

# Database connection setup
def create_database_engine(database_url: str):
    """Create database engine with proper settings"""
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False  # Set to True for SQL debugging
    )

def create_session_factory(engine):
    """Create session factory"""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_database(database_url: str):
    """Initialize database tables"""
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return engine

# Global database setup (initialized by app)
engine = None
SessionLocal = None

def get_db_session():
    """Get database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    
    session = SessionLocal()
    try:
        return session
    finally:
        pass  # Session will be closed by caller 