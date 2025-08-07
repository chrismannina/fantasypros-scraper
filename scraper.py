#!/usr/bin/env python3
"""
Updated FantasyPros Scraper - Extracts embedded JSON data from JavaScript variables
"""
import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import re
from enum import Enum
from typing import Optional, Dict, Any

class Position(Enum):
    QB = "qb"
    RB = "rb" 
    WR = "wr"
    TE = "te"
    K = "k"
    DST = "dst"
    FLEX = "flex"
    ALL = "all"  # Overall rankings

class Scoring(Enum):
    STANDARD = "standard"
    HALF_PPR = "half"
    PPR = "ppr"

# Position groups: scoring format independent vs dependent
SCORING_FORMAT_INDEPENDENT = {Position.QB, Position.K, Position.DST}  # Rankings don't change by scoring format
SCORING_FORMAT_DEPENDENT = {Position.RB, Position.WR, Position.TE, Position.FLEX}  # Rankings change by scoring format

class FantasyProsScraper:
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.fantasypros.com"
        
        # Standard headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def _build_url(self, position: Position, week: int, scoring: Scoring) -> str:
        """Build the correct FantasyPros URL based on position, week, and scoring"""
        
        if week == 0:  # Draft rankings
            if position == Position.ALL:
                # Overall draft rankings
                if scoring == Scoring.STANDARD:
                    return f"{self.base_url}/nfl/rankings/consensus-cheatsheets.php"
                elif scoring == Scoring.HALF_PPR:
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-cheatsheets.php"
                elif scoring == Scoring.PPR:
                    return f"{self.base_url}/nfl/rankings/ppr-cheatsheets.php"
            
            elif position in SCORING_FORMAT_INDEPENDENT:
                # QB, K, DST draft rankings (no scoring variants)
                return f"{self.base_url}/nfl/rankings/{position.value}-cheatsheets.php"
            
            elif position in SCORING_FORMAT_DEPENDENT:
                # RB, WR, TE, FLEX draft rankings with scoring
                if scoring == Scoring.STANDARD:
                    return f"{self.base_url}/nfl/rankings/{position.value}-cheatsheets.php"
                elif scoring == Scoring.HALF_PPR:
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-{position.value}-cheatsheets.php"
                elif scoring == Scoring.PPR:
                    return f"{self.base_url}/nfl/rankings/ppr-{position.value}-cheatsheets.php"
        
        else:  # Weekly rankings
            if position in SCORING_FORMAT_INDEPENDENT:
                # QB, K, DST weekly rankings (no scoring variants)
                return f"{self.base_url}/nfl/rankings/{position.value}.php?week={week}"
            
            elif position in SCORING_FORMAT_DEPENDENT:
                # RB, WR, TE, FLEX weekly rankings with scoring
                if scoring == Scoring.STANDARD:
                    return f"{self.base_url}/nfl/rankings/{position.value}.php?week={week}"
                elif scoring == Scoring.HALF_PPR:
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-{position.value}.php?week={week}"
                elif scoring == Scoring.PPR:
                    return f"{self.base_url}/nfl/rankings/ppr-{position.value}.php?week={week}"
            
            elif position == Position.ALL:
                # Overall weekly rankings
                if scoring == Scoring.STANDARD:
                    return f"{self.base_url}/nfl/rankings/consensus.php?week={week}"
                elif scoring == Scoring.HALF_PPR:
                    return f"{self.base_url}/nfl/rankings/half-point-ppr-consensus.php?week={week}"
                elif scoring == Scoring.PPR:
                    return f"{self.base_url}/nfl/rankings/ppr-consensus.php?week={week}"
        
        # Fallback
        return f"{self.base_url}/nfl/rankings/{position.value}.php?week={week}"
        
    def get_rankings(self, position: Position, week: int = 0, scoring: Scoring = Scoring.STANDARD) -> Optional[Dict[str, Any]]:
        """
        Get rankings for a specific position
        
        Args:
            position: Player position enum
            week: Week number (0 for draft/season rankings, 1-18 for weekly)  
            scoring: Scoring type enum
        """
        try:
            url = self._build_url(position, week, scoring)
            print(f"🌐 Fetching: {url}")
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                print("✅ Successfully retrieved page")
                return self.extract_embedded_data(response.text)
            else:
                print(f"❌ Failed to get page: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting rankings: {e}")
            return None
    
    def extract_embedded_data(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data embedded in JavaScript variables"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            
            extracted_data = {
                'ecrData': None,
                'adpData': None, 
                'expertGroupsData': None,
                'playerProps': None
            }
            
            for script in scripts:
                if script.string:
                    script_content = script.string
                    
                    # Extract various data types
                    patterns = {
                        'ecrData': r'var ecrData = ({.*?});',
                        'adpData': r'var adpData = (\[.*?\]);',
                        'expertGroupsData': r'var expertGroupsData = ({.*?});',
                        'playerProps': r'var playerProps = (\[.*?\]);'
                    }
                    
                    for data_type, pattern in patterns.items():
                        match = re.search(pattern, script_content, re.DOTALL)
                        if match:
                            try:
                                extracted_data[data_type] = json.loads(match.group(1))
                                print(f"✅ Found {data_type}")
                            except json.JSONDecodeError:
                                print(f"⚠️ Found {data_type} but couldn't parse JSON")
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ Error extracting embedded data: {e}")
            return None
    
    def process_rankings(self, extracted_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process the extracted data into a clean format"""
        try:
            if not extracted_data or not extracted_data.get('ecrData'):
                print("❌ No ranking data found")
                return None
            
            ecr_data = extracted_data['ecrData']
            adp_data = extracted_data.get('adpData', [])
            
            # Create ADP lookup for faster access
            adp_lookup = {}
            if adp_data:
                for item in adp_data:
                    if 'player_id' in item and 'rank_ecr' in item:
                        adp_lookup[item['player_id']] = item['rank_ecr']
            
            players = []
            
            # Check if ecrData has players array
            if 'players' in ecr_data:
                for player in ecr_data['players']:
                    processed_player = {
                        'rank': player.get('rank_ecr', ''),
                        'player_name': player.get('player_name', ''),
                        'team': player.get('player_team_id', ''),
                        'position': player.get('player_position_id', ''),
                        'bye_week': player.get('player_bye_week', ''),
                        'rank_min': player.get('rank_min', ''),
                        'rank_max': player.get('rank_max', ''),
                        'rank_avg': player.get('rank_ave', ''),
                        'rank_std': player.get('rank_std', ''),
                        'player_id': player.get('player_id', ''),
                    }
                    
                    # Add ADP data if available
                    if processed_player['player_id'] and processed_player['player_id'] in adp_lookup:
                        processed_player['adp_rank'] = adp_lookup[processed_player['player_id']]
                    
                    players.append(processed_player)
            
            print(f"✅ Processed {len(players)} players")
            
            return {
                'players': players,
                'metadata': {
                    'sport': ecr_data.get('sport', ''),
                    'type': ecr_data.get('type', ''),
                    'year': ecr_data.get('year', ''),
                    'week': ecr_data.get('week', ''),
                    'position': ecr_data.get('position_id', ''),
                    'scoring': ecr_data.get('scoring', ''),
                    'total_players': len(players)
                }
            }
            
        except Exception as e:
            print(f"❌ Error processing rankings: {e}")
            return None
    
    def save_data(self, data: Dict[str, Any], output_dir: str = "output", 
                  position: Position = Position.QB, week: int = 0, 
                  scoring: Scoring = Scoring.STANDARD) -> bool:
        """Save data in multiple formats"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Create filename
            week_str = f"week-{week}" if week > 0 else "draft"
            
            # Only include scoring for positions that have scoring variants
            if position in SCORING_FORMAT_INDEPENDENT:
                filename_base = f"{position.value}_{week_str}_{data['metadata']['year']}"
            else:
                filename_base = f"{position.value}_{week_str}_{scoring.value}_{data['metadata']['year']}"
            
            # Save JSON
            json_file = f"{output_dir}/{filename_base}.json"
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved JSON: {json_file}")
            
            # Save CSV
            csv_file = f"{output_dir}/{filename_base}.csv"
            if data['players']:
                with open(csv_file, 'w', newline='') as f:
                    fieldnames = data['players'][0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data['players'])
                print(f"💾 Saved CSV: {csv_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False

def main():
    """Test the updated scraper"""
    scraper = FantasyProsScraper()
    
    print("🏈 FantasyPros Scraper - Clean URLs & Data Pipeline")
    print("=" * 60)
    
    # Test different combinations
    test_cases = [
        {"position": Position.QB, "week": 1, "scoring": Scoring.STANDARD},
        {"position": Position.RB, "week": 0, "scoring": Scoring.STANDARD}, 
        {"position": Position.WR, "week": 0, "scoring": Scoring.PPR},
        {"position": Position.ALL, "week": 0, "scoring": Scoring.HALF_PPR},
    ]
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['position'].value.upper()} - Week {test_case['week']} - {test_case['scoring'].value.upper()}")
        print("-" * 40)
        
        # Get raw data
        extracted_data = scraper.get_rankings(**test_case)
        
        if extracted_data:
            # Process into clean format
            processed_data = scraper.process_rankings(extracted_data)
            
            if processed_data:
                # Save data
                scraper.save_data(processed_data, **test_case)
                
                # Show sample
                if processed_data['players']:
                    print(f"\n🎯 Sample players:")
                    for i, player in enumerate(processed_data['players'][:3]):
                        print(f"  {i+1}. {player['player_name']} ({player['team']}) - Rank {player['rank']}")
            else:
                print("❌ Failed to process data")
        else:
            print("❌ Failed to extract data")

if __name__ == "__main__":
    main() 