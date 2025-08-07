#!/usr/bin/env python3
"""
Simple API server for FantasyPros analytics
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import desc

from app.config import config
from app.database.models import get_db_session, Player, Ranking, ScrapingLog
from app.scheduler import scheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FantasyPros Analytics API",
    description="Simple API for fantasy football rankings and analytics",
    version="1.0.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "FantasyPros Analytics API",
        "version": "1.0.0",
        "current_week": config.get_current_week(),
        "current_year": config.CURRENT_YEAR
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        session = get_db_session()
        try:
            # Test database connection
            session.query(Player).limit(1).all()
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@app.get("/rankings/{position}")
async def get_rankings(
    position: str,
    week: int = Query(0, description="Week number (0 = draft)"),
    scoring: str = Query("STD", description="Scoring type: STD, PPR, HALF"),
    year: int = Query(None, description="Season year"),
    limit: int = Query(100, description="Number of players to return")
):
    """Get rankings for a position"""
    
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        session = get_db_session()
        try:
            rankings = session.query(Ranking).filter_by(
                position=position.upper(),
                week=week,
                scoring=scoring.upper(),
                year=year
            ).order_by(Ranking.rank_ecr).limit(limit).all()
            
            if not rankings:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No rankings found for {position} week {week} {scoring} {year}"
                )
            
            return {
                "position": position.upper(),
                "week": week,
                "scoring": scoring.upper(),
                "year": year,
                "count": len(rankings),
                "players": [
                    {
                        "rank": r.rank_ecr,
                        "player_name": r.player_name,
                        "team": r.team,
                        "position": r.position,
                        "rank_min": r.rank_min,
                        "rank_max": r.rank_max,
                        "rank_avg": r.rank_avg,
                        "rank_std": r.rank_std,
                        "tier": r.tier,
                        "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None
                    }
                    for r in rankings
                ]
            }
            
        finally:
            session.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/players/{player_name}")
async def get_player_rankings(
    player_name: str,
    year: int = Query(None, description="Season year")
):
    """Get all rankings for a specific player"""
    
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        session = get_db_session()
        try:
            rankings = session.query(Ranking).filter(
                Ranking.player_name.ilike(f"%{player_name}%"),
                Ranking.year == year
            ).order_by(Ranking.week, Ranking.scoring).all()
            
            if not rankings:
                raise HTTPException(
                    status_code=404,
                    detail=f"No rankings found for player '{player_name}' in {year}"
                )
            
            # Group by week and scoring
            grouped_rankings = {}
            for r in rankings:
                key = f"week_{r.week}_{r.scoring}"
                grouped_rankings[key] = {
                    "week": r.week,
                    "scoring": r.scoring,
                    "position": r.position,
                    "rank": r.rank_ecr,
                    "rank_std": r.rank_std,
                    "tier": r.tier,
                    "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None
                }
            
            return {
                "player_name": rankings[0].player_name,
                "team": rankings[0].team,
                "position": rankings[0].position,
                "year": year,
                "rankings": grouped_rankings
            }
            
        finally:
            session.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player rankings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/positions")
async def get_available_positions():
    """Get list of available positions with data"""
    try:
        session = get_db_session()
        try:
            positions = session.query(Ranking.position).distinct().all()
            return {
                "positions": [pos[0] for pos in positions if pos[0]]
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/weeks")
async def get_available_weeks(year: int = Query(None)):
    """Get list of available weeks with data"""
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        session = get_db_session()
        try:
            weeks = session.query(Ranking.week).filter_by(year=year).distinct().order_by(Ranking.week).all()
            return {
                "year": year,
                "weeks": [week[0] for week in weeks if week[0] is not None]
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting weeks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        session = get_db_session()
        try:
            # Count players and rankings
            player_count = session.query(Player).count()
            ranking_count = session.query(Ranking).count()
            
            # Recent scraping activity
            recent_logs = session.query(ScrapingLog).order_by(desc(ScrapingLog.started_at)).limit(10).all()
            
            # Success rate over last 24 hours
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_success = session.query(ScrapingLog).filter(
                ScrapingLog.started_at >= yesterday,
                ScrapingLog.success == True
            ).count()
            recent_total = session.query(ScrapingLog).filter(
                ScrapingLog.started_at >= yesterday
            ).count()
            
            success_rate = (recent_success / recent_total * 100) if recent_total > 0 else 0
            
            return {
                "players": player_count,
                "rankings": ranking_count,
                "success_rate_24h": round(success_rate, 1),
                "recent_jobs": [
                    {
                        "position": log.position,
                        "scoring": log.scoring,
                        "week": log.week,
                        "success": log.success,
                        "players_scraped": log.players_scraped,
                        "started_at": log.started_at.isoformat(),
                        "duration": log.duration_seconds
                    }
                    for log in recent_logs
                ]
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Manual job endpoints (for admin/debugging)
@app.post("/admin/scrape/draft")
async def trigger_draft_scrape(year: int = Query(None)):
    """Manually trigger draft scraping"""
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        results = scheduler.run_manual_job('draft', year=year)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return {
            "message": "Draft scraping completed",
            "success_count": success_count,
            "total_count": total_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Manual draft scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/admin/scrape/weekly")
async def trigger_weekly_scrape(
    week: int = Query(None),
    year: int = Query(None)
):
    """Manually trigger weekly scraping"""
    if week is None:
        week = config.get_current_week()
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        results = scheduler.run_manual_job('weekly', week=week, year=year)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return {
            "message": f"Weekly scraping completed for week {week}",
            "week": week,
            "success_count": success_count,
            "total_count": total_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Manual weekly scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/admin/scrape/position")
async def trigger_position_scrape(
    position: str,
    week: int = Query(0),
    scoring: str = Query("STD"),
    year: int = Query(None)
):
    """Manually trigger position scraping"""
    if year is None:
        year = config.CURRENT_YEAR
    
    try:
        success = scheduler.run_manual_job(
            'position',
            position=position.upper(),
            week=week,
            scoring=scoring.upper(),
            year=year
        )
        
        return {
            "message": f"Position scraping completed",
            "position": position.upper(),
            "week": week,
            "scoring": scoring.upper(),
            "success": success
        }
        
    except Exception as e:
        logger.error(f"Manual position scrape failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT) 