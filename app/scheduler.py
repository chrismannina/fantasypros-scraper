#!/usr/bin/env python3
"""
Simple scheduler for FantasyPros data collection
"""
import schedule
import time
import logging
from datetime import datetime
import threading

from app.config import config
from app.scraper.fantasypros import scraper

logger = logging.getLogger(__name__)

class SimpleScheduler:
    """Simple scheduler for data collection"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def setup_schedules(self):
        """Setup automated schedules"""
        current_week = config.get_current_week()
        
        if current_week == 0:
            # Draft season - run every 6 hours
            schedule.every(6).hours.do(self.run_draft_update)
            logger.info("Scheduled draft updates every 6 hours")
        else:
            # Regular season - run 3 times daily
            schedule.every().day.at("08:00").do(self.run_weekly_update)
            schedule.every().day.at("14:00").do(self.run_weekly_update)
            schedule.every().day.at("20:00").do(self.run_weekly_update)
            logger.info("Scheduled weekly updates at 8AM, 2PM, 8PM")
        
        # Health check every 30 minutes
        schedule.every(30).minutes.do(self.health_check)
    
    def run_draft_update(self):
        """Run draft rankings update"""
        try:
            logger.info("Starting scheduled draft update")
            results = scraper.scrape_all_draft()
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Draft update completed: {success_count}/{total_count} successful")
            
            if success_count == 0:
                logger.error("All draft scraping jobs failed!")
            elif success_count < total_count * 0.7:
                logger.warning(f"Low success rate: {success_count}/{total_count}")
                
        except Exception as e:
            logger.error(f"Draft update failed: {e}")
    
    def run_weekly_update(self):
        """Run weekly rankings update"""
        try:
            logger.info("Starting scheduled weekly update")
            current_week = config.get_current_week()
            
            if current_week == 0:
                # Switch to draft if we're in draft season
                self.run_draft_update()
                return
            
            results = scraper.scrape_all_weekly(current_week)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Weekly update completed: {success_count}/{total_count} successful")
            
            if success_count == 0:
                logger.error("All weekly scraping jobs failed!")
            elif success_count < total_count * 0.7:
                logger.warning(f"Low success rate: {success_count}/{total_count}")
                
        except Exception as e:
            logger.error(f"Weekly update failed: {e}")
    
    def health_check(self):
        """Simple health check"""
        try:
            from app.database.models import get_db_session, ScrapingLog
            
            session = get_db_session()
            try:
                # Check if we can query the database
                recent_logs = session.query(ScrapingLog).limit(1).all()
                logger.debug("Health check passed")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.setup_schedules()
        self.running = True
        
        def run_scheduler():
            logger.info("Scheduler started")
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def run_manual_job(self, job_type: str, **kwargs):
        """Run a manual job"""
        if job_type == 'draft':
            return scraper.scrape_all_draft(kwargs.get('year'))
        elif job_type == 'weekly':
            return scraper.scrape_all_weekly(kwargs.get('week'), kwargs.get('year'))
        elif job_type == 'position':
            return scraper.scrape_position(
                kwargs.get('position'),
                kwargs.get('week', 0),
                kwargs.get('scoring', 'STD'),
                kwargs.get('year')
            )
        else:
            raise ValueError(f"Unknown job type: {job_type}")

# Global scheduler instance
scheduler = SimpleScheduler() 