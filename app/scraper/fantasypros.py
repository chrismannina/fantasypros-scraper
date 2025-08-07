#!/usr/bin/env python3
"""
Clean FantasyPros scraper - focused and simple
"""
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests
from bs4 import BeautifulSoup
import json
import re

from app.config import config
from app.database.models import get_db_session, Player, Ranking, ScrapingLog

logger = logging.getLogger(__name__)

# Position groups - keep the logic that works
SCORING_INDEPENDENT = {'QB', 'K', 'DST'}  # No scoring variants
SCORING_DEPENDENT = {'RB', 'WR', 'TE', 'FLEX'}  # Have scoring variants

class FantasyProsScraper:
    """Simple, clean FantasyPros scraper"""
    
    def __init__(self):
        self.base_url = "https://www.fantasypros.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def build_url(self, position: str, week: int, scoring: str = 'STD') -> str:
        """Build FantasyPros URL - keep the working logic"""
        
        if week == 0:  # Draft rankings
            if position == 'ALL':
                if scoring == 'STD':
                    return f"{self.base_url}/nfl/rankings/consensus-cheatsheets.php"
                elif scoring == 'HALF':
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-cheatsheets.php"
                elif scoring == 'PPR':
                    return f"{self.base_url}/nfl/rankings/ppr-cheatsheets.php"
            
            elif position in SCORING_INDEPENDENT:
                return f"{self.base_url}/nfl/rankings/{position.lower()}-cheatsheets.php"
            
            elif position in SCORING_DEPENDENT:
                if scoring == 'STD':
                    return f"{self.base_url}/nfl/rankings/{position.lower()}-cheatsheets.php"
                elif scoring == 'HALF':
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-{position.lower()}-cheatsheets.php"
                elif scoring == 'PPR':
                    return f"{self.base_url}/nfl/rankings/ppr-{position.lower()}-cheatsheets.php"
        
        else:  # Weekly rankings
            if position in SCORING_INDEPENDENT:
                return f"{self.base_url}/nfl/rankings/{position.lower()}.php?week={week}"
            
            elif position in SCORING_DEPENDENT:
                if scoring == 'STD':
                    return f"{self.base_url}/nfl/rankings/{position.lower()}.php?week={week}"
                elif scoring == 'HALF':
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-{position.lower()}.php?week={week}"
                elif scoring == 'PPR':
                    return f"{self.base_url}/nfl/rankings/ppr-{position.lower()}.php?week={week}"
        
        # Fallback
        return f"{self.base_url}/nfl/rankings/{position.lower()}.php?week={week}"
    
    def extract_data(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract embedded JSON data"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for script in soup.find_all('script'):
                if script.string and 'var ecrData = ' in script.string:
                    # Extract ecrData
                    match = re.search(r'var ecrData = ({.*?});', script.string, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract data: {e}")
            return None
    
    def scrape_position(self, position: str, week: int = 0, scoring: str = 'STD', year: int = None) -> bool:
        """Scrape rankings for a position"""
        if year is None:
            year = config.CURRENT_YEAR
        
        start_time = time.time()
        log_entry = None
        
        try:
            # Rate limiting
            time.sleep(config.SCRAPING_DELAY)
            
            # Build URL and fetch
            url = self.build_url(position, week, scoring)
            logger.info(f"Scraping {position} {scoring} week {week}: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract data
            data = self.extract_data(response.text)
            if not data or 'players' not in data:
                logger.warning(f"No data found for {position} {scoring} week {week}")
                return False
            
            # Store in database
            session = get_db_session()
            players_count = 0
            
            try:
                for player_data in data['players']:
                    # Get player info
                    player_id = str(player_data.get('player_id', ''))
                    if not player_id:
                        continue
                    
                    player_name = player_data.get('player_name', '')
                    team = player_data.get('player_team_id', '')
                    pos = player_data.get('player_position_id', position)
                    bye_week = self._safe_int(player_data.get('player_bye_week'))
                    
                    # Upsert player
                    player = session.query(Player).filter_by(id=player_id).first()
                    if not player:
                        player = Player(
                            id=player_id,
                            name=player_name,
                            position=pos,
                            team=team,
                            bye_week=bye_week
                        )
                        session.add(player)
                    else:
                        player.name = player_name
                        player.team = team
                        player.bye_week = bye_week
                        player.updated_at = datetime.now()
                    
                    # Upsert ranking
                    ranking = session.query(Ranking).filter_by(
                        player_id=player_id,
                        year=year,
                        week=week,
                        scoring=scoring
                    ).first()
                    
                    if not ranking:
                        ranking = Ranking(
                            player_id=player_id,
                            player_name=player_name,
                            position=pos,
                            team=team,
                            year=year,
                            week=week,
                            scoring=scoring
                        )
                        session.add(ranking)
                    
                    # Update ranking data
                    ranking.rank_ecr = self._safe_int(player_data.get('rank_ecr'))
                    ranking.rank_min = self._safe_int(player_data.get('rank_min'))
                    ranking.rank_max = self._safe_int(player_data.get('rank_max'))
                    ranking.rank_avg = self._safe_float(player_data.get('rank_ave'))
                    ranking.rank_std = self._safe_float(player_data.get('rank_std'))
                    ranking.scraped_at = datetime.now()
                    
                    players_count += 1
                
                # Log success
                duration = time.time() - start_time
                log_entry = ScrapingLog(
                    position=position,
                    scoring=scoring,
                    week=week,
                    year=year,
                    success=True,
                    players_scraped=players_count,
                    completed_at=datetime.now(),
                    duration_seconds=duration
                )
                session.add(log_entry)
                
                session.commit()
                logger.info(f"Successfully scraped {players_count} players for {position} {scoring} week {week}")
                return True
                
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except Exception as e:
            # Log failure
            duration = time.time() - start_time
            session = get_db_session()
            try:
                log_entry = ScrapingLog(
                    position=position,
                    scoring=scoring,
                    week=week,
                    year=year,
                    success=False,
                    players_scraped=0,
                    error_message=str(e),
                    completed_at=datetime.now(),
                    duration_seconds=duration
                )
                session.add(log_entry)
                session.commit()
            except:
                pass
            finally:
                session.close()
            
            logger.error(f"Failed to scrape {position} {scoring} week {week}: {e}")
            return False
    
    def scrape_all_draft(self, year: int = None) -> Dict[str, bool]:
        """Scrape all draft rankings"""
        if year is None:
            year = config.CURRENT_YEAR
        
        results = {}
        
        # QB, K, DST (scoring independent)
        for position in ['QB', 'K', 'DST']:
            results[f"{position}_STD"] = self.scrape_position(position, 0, 'STD', year)
        
        # RB, WR, TE (scoring dependent)
        for position in ['RB', 'WR', 'TE']:
            for scoring in ['STD', 'PPR', 'HALF']:
                results[f"{position}_{scoring}"] = self.scrape_position(position, 0, scoring, year)
        
        # Overall rankings
        for scoring in ['STD', 'PPR', 'HALF']:
            results[f"ALL_{scoring}"] = self.scrape_position('ALL', 0, scoring, year)
        
        return results
    
    def scrape_all_weekly(self, week: int = None, year: int = None) -> Dict[str, bool]:
        """Scrape all weekly rankings"""
        if week is None:
            week = config.get_current_week()
        if year is None:
            year = config.CURRENT_YEAR
        
        if week == 0:
            return self.scrape_all_draft(year)
        
        results = {}
        
        # QB, K, DST (scoring independent)
        for position in ['QB', 'K', 'DST']:
            results[f"{position}_STD"] = self.scrape_position(position, week, 'STD', year)
        
        # RB, WR, TE, FLEX (scoring dependent)
        for position in ['RB', 'WR', 'TE', 'FLEX']:
            for scoring in ['STD', 'PPR', 'HALF']:
                results[f"{position}_{scoring}"] = self.scrape_position(position, week, scoring, year)
        
        return results
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        if value is None or value == '':
            return None
        try:
            return int(float(str(value)))
        except:
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float"""
        if value is None or value == '':
            return None
        try:
            return float(str(value))
        except:
            return None

# Create global scraper instance
scraper = FantasyProsScraper() 