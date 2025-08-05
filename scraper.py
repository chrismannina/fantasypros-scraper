#!/usr/bin/env python3
"""
FantasyPros Expert Rankings Scraper
Uses strategic pairing to deduce individual expert rankings from consensus data
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from playwright.async_api import Page, async_playwright, expect
from dotenv import load_dotenv
import colorlog
import numpy as np

# Load environment variables
load_dotenv()

# Setup colored logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel('INFO')


class FantasyProsScraper:
    """Main scraper class for FantasyPros expert rankings"""
    
    def __init__(self):
        """Initialize scraper with configuration from environment"""
        self.email = os.getenv('FANTASYPROS_EMAIL')
        self.password = os.getenv('FANTASYPROS_PASSWORD')
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        self.timeout = int(os.getenv('TIMEOUT', '60000'))
        self.delay = int(os.getenv('DELAY_BETWEEN_REQUESTS', '2000'))
        self.output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        self.save_screenshots = os.getenv('SAVE_SCREENSHOTS', 'false').lower() == 'true'
        self.max_experts = int(os.getenv('MAX_EXPERTS_TO_SCRAPE', '50'))
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        if self.save_screenshots:
            (self.output_dir / 'screenshots').mkdir(exist_ok=True)
        
        # Data storage
        self.player_map: Dict[str, str] = {}
        self.expert_rankings: Dict[str, Dict[str, float]] = {}
        self.experts_list: List[str] = []
        
        # URLs
        self.base_url = "https://www.fantasypros.com"
        self.rankings_url = f"{self.base_url}/nfl/rankings/half-point-ppr-cheatsheets.php"
    
    def validate_config(self) -> bool:
        """Validate required configuration"""
        if not self.email or not self.password:
            logger.error("Missing FANTASYPROS_EMAIL or FANTASYPROS_PASSWORD in environment")
            return False
        return True
    
    async def handle_cookie_consent(self, page: Page) -> None:
        """Handle cookie consent banner if it appears"""
        try:
            await page.get_by_role("button", name="Accept Cookies").click(timeout=5000)
            logger.info("Accepted cookie consent")
        except Exception:
            logger.debug("Cookie banner not found or already accepted")
    
    async def login(self, page: Page) -> bool:
        """Login to FantasyPros if required"""
        try:
            # Check if login is required
            login_link = page.locator("a:has-text('Login')")
            if await login_link.count() > 0:
                logger.info("Login required, authenticating...")
                await login_link.click()
                
                # Fill login form
                await page.fill("input[name='email']", self.email)
                await page.fill("input[name='password']", self.password)
                await page.click("button[type='submit']")
                
                # Wait for navigation
                await page.wait_for_load_state("networkidle")
                logger.info("Login successful")
                return True
            else:
                logger.info("Already logged in or login not required")
                return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def get_available_experts(self, page: Page) -> List[str]:
        """Get list of all available experts from the modal"""
        logger.info("Fetching available experts...")
        
        # Open expert selection modal
        await page.get_by_role("button", name="Pick Experts").click()
        
        experts_modal = page.locator(".experts-modal")
        await expect(experts_modal).to_be_visible()
        
        # Get all expert rows
        expert_rows = await page.locator(".experts-modal-table__expert").all()
        experts = []
        
        for row in expert_rows:
            try:
                # Get expert name from the row
                name_element = row.locator(".yearbook-block__title-link")
                if await name_element.count() > 0:
                    expert_name = await name_element.inner_text()
                    
                    # Get site name
                    site_element = row.locator(".yearbook-block__description-text")
                    site_name = await site_element.inner_text() if await site_element.count() > 0 else ""
                    
                    # Format as "Name (Site)"
                    full_name = f"{expert_name.strip()} ({site_name.strip()})" if site_name else expert_name.strip()
                    experts.append(full_name)
            except Exception as e:
                logger.debug(f"Error parsing expert row: {e}")
                continue
        
        # Close modal
        await page.click("button.experts-modal__header-close")
        await page.wait_for_timeout(500)
        
        logger.info(f"Found {len(experts)} available experts")
        return experts
    
    async def select_expert_pair(self, page: Page, expert1: str, expert2: str) -> bool:
        """Select exactly two experts in the modal"""
        try:
            # Open expert selection modal
            await page.get_by_role("button", name="Pick Experts").click()
            
            experts_modal = page.locator(".experts-modal")
            await expect(experts_modal).to_be_visible()
            
            # Clear all selections
            clear_button = experts_modal.get_by_role("button", name="Clear All")
            if await clear_button.is_visible():
                await clear_button.click()
                await page.wait_for_timeout(500)
            
            # Find and select the two experts
            selected_count = 0
            expert_rows = await page.locator(".experts-modal-table__expert").all()
            
            for row in expert_rows:
                try:
                    name_element = row.locator(".yearbook-block__title-link")
                    if await name_element.count() > 0:
                        row_expert_name = await name_element.inner_text()
                        site_element = row.locator(".yearbook-block__description-text")
                        site_name = await site_element.inner_text() if await site_element.count() > 0 else ""
                        full_name = f"{row_expert_name.strip()} ({site_name.strip()})" if site_name else row_expert_name.strip()
                        
                        if full_name in [expert1, expert2]:
                            checkbox = row.locator("input[type='checkbox']")
                            await checkbox.check()
                            selected_count += 1
                            logger.debug(f"Selected expert: {full_name}")
                            
                            if selected_count == 2:
                                break
                except Exception as e:
                    logger.debug(f"Error selecting expert: {e}")
                    continue
            
            if selected_count != 2:
                logger.error(f"Could not select both experts. Selected: {selected_count}")
                await page.click("button.experts-modal__header-close")
                return False
            
            # Update rankings
            await experts_modal.get_by_role("button", name="Update Rankings").click()
            
            # Wait for modal to close and rankings to update
            await expect(experts_modal).not_to_be_visible()
            await page.wait_for_timeout(self.delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Error selecting expert pair: {e}")
            return False
    
    async def scrape_consensus_rankings(self, page: Page) -> Dict[str, int]:
        """Scrape consensus rankings from the current page"""
        rankings = {}
        
        # Wait for table to load
        await expect(page.locator("#ranking-table tbody tr[data-tier='1']")).to_be_visible()
        
        # Get all player rows
        rows = await page.locator("#ranking-table tbody tr.player-row").all()
        
        for row in rows:
            try:
                # Get rank
                rank_text = await row.locator("td:first-child").inner_text()
                rank = int(rank_text.strip())
                
                # Get player info
                player_link = row.locator("a.fp-player-link")
                if await player_link.count() > 0:
                    player_name = await player_link.get_attribute("fp-player-name")
                    player_id = await player_link.get_attribute("fp-player-id")
                    
                    if player_id and player_name:
                        rankings[player_id] = rank
                        self.player_map[player_id] = player_name
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue
        
        logger.debug(f"Scraped {len(rankings)} player rankings")
        return rankings
    
    async def get_consensus_for_pair(self, page: Page, expert1: str, expert2: str) -> Optional[Dict[str, int]]:
        """Get consensus rankings for a specific pair of experts"""
        logger.info(f"Getting consensus for: {expert1} + {expert2}")
        
        if not await self.select_expert_pair(page, expert1, expert2):
            return None
        
        rankings = await self.scrape_consensus_rankings(page)
        
        if self.save_screenshots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{expert1.replace(' ', '_')}_{expert2.replace(' ', '_')}_{timestamp}.png"
            await page.screenshot(path=self.output_dir / 'screenshots' / filename)
        
        return rankings
    
    def deduce_individual_rankings(self, expert_a: str, expert_b: str, expert_c: str,
                                 avg_ab: Dict[str, int], avg_ac: Dict[str, int], 
                                 avg_bc: Dict[str, int]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """
        Deduce individual rankings using the algebraic method:
        rank_A = avg(A,B) + avg(A,C) - avg(B,C)
        rank_B = 2 * avg(A,B) - rank_A
        rank_C = 2 * avg(A,C) - rank_A
        """
        ranks_a, ranks_b, ranks_c = {}, {}, {}
        
        # Get all player IDs that appear in all three consensus rankings
        all_players = set(avg_ab.keys()) & set(avg_ac.keys()) & set(avg_bc.keys())
        
        for player_id in all_players:
            # Apply the algebraic formulas
            rank_a = avg_ab[player_id] + avg_ac[player_id] - avg_bc[player_id]
            rank_b = 2 * avg_ab[player_id] - rank_a
            rank_c = 2 * avg_ac[player_id] - rank_a
            
            ranks_a[player_id] = rank_a
            ranks_b[player_id] = rank_b
            ranks_c[player_id] = rank_c
        
        logger.info(f"Deduced rankings for {len(all_players)} players")
        return ranks_a, ranks_b, ranks_c
    
    def deduce_expert_ranking(self, baseline_ranks: Dict[str, float], 
                            consensus_ranks: Dict[str, int]) -> Dict[str, float]:
        """
        Deduce individual expert ranking using baseline:
        rank_X = 2 * avg(baseline, X) - rank_baseline
        """
        target_ranks = {}
        
        for player_id in consensus_ranks:
            if player_id in baseline_ranks:
                rank_target = 2 * consensus_ranks[player_id] - baseline_ranks[player_id]
                target_ranks[player_id] = rank_target
        
        return target_ranks
    
    async def scrape_all_experts(self, page: Page) -> None:
        """Main scraping logic to get all expert rankings"""
        # Get available experts
        available_experts = await self.get_available_experts(page)
        
        if len(available_experts) < 3:
            logger.error("Need at least 3 experts to run deduction algorithm")
            return
        
        # Get specific experts from env or use all available
        specific_experts = os.getenv('SPECIFIC_EXPERTS', '').strip()
        if specific_experts:
            self.experts_list = [e.strip() for e in specific_experts.split(',') if e.strip() in available_experts]
        else:
            self.experts_list = available_experts[:self.max_experts]
        
        if len(self.experts_list) < 3:
            logger.error("Not enough valid experts specified")
            return
        
        logger.info(f"Will scrape {len(self.experts_list)} experts")
        
        # Part A: Establish baseline with first 3 experts
        logger.info("\n=== PART A: Establishing baseline rankings ===")
        expert_a, expert_b, expert_c = self.experts_list[0], self.experts_list[1], self.experts_list[2]
        
        # Get the three necessary consensus rankings
        avg_ab = await self.get_consensus_for_pair(page, expert_a, expert_b)
        if not avg_ab:
            logger.error("Failed to get consensus for first pair")
            return
        
        avg_ac = await self.get_consensus_for_pair(page, expert_a, expert_c)
        if not avg_ac:
            logger.error("Failed to get consensus for second pair")
            return
        
        avg_bc = await self.get_consensus_for_pair(page, expert_b, expert_c)
        if not avg_bc:
            logger.error("Failed to get consensus for third pair")
            return
        
        # Deduce individual rankings for the baseline experts
        ranks_a, ranks_b, ranks_c = self.deduce_individual_rankings(
            expert_a, expert_b, expert_c, avg_ab, avg_ac, avg_bc
        )
        
        self.expert_rankings[expert_a] = ranks_a
        self.expert_rankings[expert_b] = ranks_b
        self.expert_rankings[expert_c] = ranks_c
        
        logger.info(f"Successfully deduced baseline rankings for {expert_a}, {expert_b}, {expert_c}")
        
        # Part B: Deduce all other experts using the baseline
        logger.info("\n=== PART B: Deducing remaining expert rankings ===")
        baseline_expert = expert_a
        baseline_ranks = ranks_a
        
        for i in range(3, len(self.experts_list)):
            target_expert = self.experts_list[i]
            logger.info(f"\nProcessing expert {i+1}/{len(self.experts_list)}: {target_expert}")
            
            consensus = await self.get_consensus_for_pair(page, baseline_expert, target_expert)
            if not consensus:
                logger.warning(f"Failed to get consensus for {target_expert}, skipping")
                continue
            
            target_ranks = self.deduce_expert_ranking(baseline_ranks, consensus)
            self.expert_rankings[target_expert] = target_ranks
            
            logger.info(f"Successfully deduced rankings for {target_expert}")
    
    def save_results(self) -> None:
        """Save scraped data in multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw deduced rankings as JSON
        raw_data_file = self.output_dir / f"deduced_rankings_{timestamp}.json"
        with open(raw_data_file, 'w') as f:
            json.dump(self.expert_rankings, f, indent=2)
        logger.info(f"Saved raw rankings to {raw_data_file}")
        
        # Save player mapping
        player_map_file = self.output_dir / f"player_map_{timestamp}.json"
        with open(player_map_file, 'w') as f:
            json.dump(self.player_map, f, indent=2)
        logger.info(f"Saved player map to {player_map_file}")
        
        # Create DataFrame for analysis
        df_data = []
        for player_id, player_name in self.player_map.items():
            row = {
                "Player ID": player_id,
                "Player": player_name
            }
            
            # Add each expert's ranking
            for expert_name in self.experts_list:
                if expert_name in self.expert_rankings:
                    row[expert_name] = self.expert_rankings[expert_name].get(player_id, None)
            
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        # Calculate average rank and standard deviation
        expert_columns = [col for col in df.columns if col not in ["Player ID", "Player"]]
        df["Average Rank"] = df[expert_columns].mean(axis=1, skipna=True)
        df["Std Dev"] = df[expert_columns].std(axis=1, skipna=True)
        df["Expert Count"] = df[expert_columns].count(axis=1)
        
        # Sort by average rank
        df = df.sort_values("Average Rank")
        
        # Save as CSV
        csv_file = self.output_dir / f"expert_rankings_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        logger.info(f"Saved rankings CSV to {csv_file}")
        
        # Save as Excel with formatting
        excel_file = self.output_dir / f"expert_rankings_{timestamp}.xlsx"
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rankings', index=False)
            
            # Add a summary sheet
            summary_data = {
                "Metric": ["Total Experts", "Total Players", "Scrape Date", "URL"],
                "Value": [len(self.experts_list), len(self.player_map), 
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.rankings_url]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        logger.info(f"Saved rankings Excel to {excel_file}")
        
        # Print summary statistics
        logger.info("\n=== SCRAPING SUMMARY ===")
        logger.info(f"Total experts scraped: {len(self.expert_rankings)}")
        logger.info(f"Total players tracked: {len(self.player_map)}")
        logger.info(f"Average rankings per player: {df['Expert Count'].mean():.1f}")
    
    async def run(self) -> None:
        """Main execution method"""
        if not self.validate_config():
            sys.exit(1)
        
        async with async_playwright() as p:
            logger.info("Launching browser...")
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to rankings page
                logger.info(f"Navigating to {self.rankings_url}")
                await page.goto(self.rankings_url, wait_until="domcontentloaded", timeout=self.timeout)
                
                # Handle cookie consent
                await self.handle_cookie_consent(page)
                
                # Login if required
                if not await self.login(page):
                    logger.error("Login failed, cannot proceed")
                    return
                
                # Wait for page to fully load
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # Start scraping
                await self.scrape_all_experts(page)
                
                # Save results
                if self.expert_rankings:
                    self.save_results()
                else:
                    logger.warning("No rankings were scraped")
                
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                if self.save_screenshots:
                    error_screenshot = self.output_dir / 'screenshots' / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=error_screenshot)
                    logger.info(f"Error screenshot saved to {error_screenshot}")
                raise
            finally:
                await browser.close()
                logger.info("Browser closed")


async def main():
    """Entry point"""
    scraper = FantasyProsScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main()) 