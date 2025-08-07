#!/usr/bin/env python3
"""
Main application entry point
"""
import sys
import logging
import argparse
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.config import config
from app.database.models import init_database, create_database_engine, create_session_factory, SessionLocal, engine

logger = logging.getLogger(__name__)

def init_app():
    """Initialize the application"""
    try:
        logger.info("Initializing FantasyPros Analytics")
        logger.info(f"Current year: {config.CURRENT_YEAR}")
        logger.info(f"Current week: {config.get_current_week()}")
        
        # Initialize database
        logger.info("Setting up database...")
        global engine, SessionLocal
        engine = init_database(config.DATABASE_URL)
        SessionLocal = create_session_factory(engine)
        
        # Update the global session factory in models
        import app.database.models as models
        models.engine = engine
        models.SessionLocal = SessionLocal
        
        logger.info("Application initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        return False

def run_scraper(args):
    """Run manual scraping"""
    from app.scraper.fantasypros import scraper
    
    logger.info(f"Starting manual scrape...")
    
    if args.position:
        # Scrape specific position
        success = scraper.scrape_position(
            args.position.upper(),
            args.week,
            args.scoring.upper(),
            args.year
        )
        print(f"Scraping {'succeeded' if success else 'failed'}")
        return 0 if success else 1
    
    elif args.week == 0:
        # Draft scraping
        results = scraper.scrape_all_draft(args.year)
    else:
        # Weekly scraping
        results = scraper.scrape_all_weekly(args.week, args.year)
    
    # Print results
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"Scraping completed: {success_count}/{total_count} successful")
    
    for job, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {job}")
    
    return 0 if success_count > 0 else 1

def run_server(args):
    """Run the API server"""
    import uvicorn
    from app.api.server import app
    
    logger.info(f"Starting API server on port {config.PORT}")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=config.PORT,
            reload=config.DEBUG
        )
    except KeyboardInterrupt:
        logger.info("Server stopped")
    
    return 0

def run_scheduler(args):
    """Run the automated scheduler"""
    from app.scheduler import scheduler
    
    logger.info("Starting automated scheduler...")
    
    try:
        scheduler.start()
        
        # Keep running until interrupted
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.stop()
    
    return 0

def show_status(args):
    """Show system status"""
    from app.database.models import get_db_session, Player, Ranking, ScrapingLog
    from sqlalchemy import desc
    
    try:
        session = get_db_session()
        try:
            # Database stats
            player_count = session.query(Player).count()
            ranking_count = session.query(Ranking).count()
            
            # Recent activity
            recent_logs = session.query(ScrapingLog).order_by(desc(ScrapingLog.started_at)).limit(5).all()
            
            print("🏈 FantasyPros Analytics Status")
            print("=" * 40)
            print(f"Database: {config.DATABASE_URL}")
            print(f"Current Year: {config.CURRENT_YEAR}")
            print(f"Current Week: {config.get_current_week()}")
            print(f"Players: {player_count}")
            print(f"Rankings: {ranking_count}")
            print()
            
            if recent_logs:
                print("Recent Scraping Activity:")
                for log in recent_logs:
                    status = "✅" if log.success else "❌"
                    duration = f"{log.duration_seconds:.1f}s" if log.duration_seconds else "N/A"
                    print(f"  {status} {log.position} {log.scoring} week {log.week} - {log.players_scraped} players ({duration})")
            else:
                print("No recent scraping activity")
            
            return 0
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="FantasyPros Analytics - Simple fantasy football data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py init                                    # Initialize database
  python main.py scrape --week 0                        # Scrape all draft rankings
  python main.py scrape --position QB --week 1          # Scrape QB week 1
  python main.py server                                  # Start API server
  python main.py scheduler                               # Start automated scheduler
  python main.py status                                  # Show system status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize database')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Run manual scraping')
    scrape_parser.add_argument('--position', 
                              choices=['QB', 'RB', 'WR', 'TE', 'K', 'DST', 'FLEX', 'ALL'],
                              help='Specific position to scrape')
    scrape_parser.add_argument('--week', type=int, default=0,
                              help='Week to scrape (0 = draft)')
    scrape_parser.add_argument('--scoring', 
                              choices=['STD', 'PPR', 'HALF'],
                              default='STD',
                              help='Scoring type')
    scrape_parser.add_argument('--year', type=int, default=config.CURRENT_YEAR,
                              help='Season year')
    
    # Server command
    subparsers.add_parser('server', help='Start API server')
    
    # Scheduler command
    subparsers.add_parser('scheduler', help='Start automated scheduler')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize app for all commands
    if not init_app():
        return 1
    
    # Run command
    try:
        if args.command == 'init':
            print("✅ Database initialized successfully")
            return 0
        elif args.command == 'scrape':
            return run_scraper(args)
        elif args.command == 'server':
            return run_server(args)
        elif args.command == 'scheduler':
            return run_scheduler(args)
        elif args.command == 'status':
            return show_status(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 