
import asyncio
import os
import csv
import json
from typing import List, Dict, Any
from playwright.async_api import Page, async_playwright, expect
from dotenv import load_dotenv
import colorlog
from pathlib import Path

# Load environment variables
load_dotenv()

# Timing constants - adjust this multiplier for faster/slower execution
# Set to 0.1 for super fast testing, 1.0 for normal, 2.0 for slow connections
WAIT_MULTIPLIER = float(os.getenv('WAIT_MULTIPLIER', '0.2'))  # Default to 0.2 for testing

# Individual wait times (in milliseconds) - these get multiplied by WAIT_MULTIPLIER
WAIT_TIMES = {
    'modal_render': 1000,      # Wait for modal to fully render
    'state_update': 500,       # Wait after checkbox state changes  
    'scroll': 300,             # Wait after scrolling
    'click': 200,              # Wait after clicks
    'page_update': 2000,       # Wait for page to update after apply
    'verification': 5000,      # Pause for manual verification (set to 0 to skip)
}

def wait_time(key: str) -> int:
    """Get adjusted wait time based on multiplier"""
    return int(WAIT_TIMES.get(key, 1000) * WAIT_MULTIPLIER)

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
logger.setLevel('DEBUG')  # This will show all debug messages


class FantasyProsNewScraper:
    """
    A simplified scraper to log in, navigate to rankings, and select experts.
    """

    def __init__(self):
        """Initialize scraper with configuration from environment"""
        self.email = os.getenv('FANTASYPROS_EMAIL')
        self.password = os.getenv('FANTASYPROS_PASSWORD')
        self.headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        self.timeout = int(os.getenv('TIMEOUT', '60000'))
        self.output_dir = Path(os.getenv('OUTPUT_DIR', 'output'))
        
        # URLs
        self.base_url = "https://www.fantasypros.com"
        self.login_url = f"{self.base_url}/accounts/signin/"
        self.post_login_url = f"{self.base_url}/?signedin"
        self.rankings_url = f"{self.base_url}/nfl/rankings/half-point-ppr-cheatsheets.php"

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / 'screenshots').mkdir(exist_ok=True)

    async def run(self):
        """Main execution method"""
        logger.info(f"Starting with wait multiplier: {WAIT_MULTIPLIER}x (set WAIT_MULTIPLIER env var to adjust)")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                if not await self.login(page):
                    logger.error("Login failed. Exiting.")
                    return

                await self.select_experts(page)
                
                # Scrape the rankings table after expert selection
                await self.scrape_rankings_table(page)

            except Exception as e:
                logger.error(f"An error occurred: {e}")
            finally:
                logger.info("Closing browser.")
                await browser.close()

    async def login(self, page: Page) -> bool:
        logger.info(f"Navigating to login page: {self.login_url}")
        await page.goto(self.login_url, timeout=self.timeout)

        logger.info("Entering credentials...")
        await page.fill("#username", self.email)
        await page.fill("#password", self.password)

        logger.info("Submitting login form...")
        await page.click("button[type='submit']")

        try:
            # Wait for navigation away from the signin page
            await page.wait_for_url(lambda url: "signin" not in url, timeout=15000)
            logger.info("Login successful!")
            logger.info(f"Current URL: {page.url}")
            return True
        except Exception:
            logger.error("Failed to redirect after login.")
            return False

    async def select_experts(self, page: Page) -> None:
        logger.info(f"Navigating to rankings page: {self.rankings_url}")
        await page.goto(self.rankings_url, timeout=self.timeout)

        logger.info("Opening 'Pick Experts' modal...")
        # Use text selector like the working JavaScript version
        await page.click('text="Pick Experts"')

        # Wait for modal to be visible
        experts_modal = page.locator(".experts-modal")
        await expect(experts_modal).to_be_visible(timeout=self.timeout)
        logger.info("Expert modal is open.")
        
        # Wait for expert checkboxes to be loaded in the modal
        logger.info("Waiting for expert checkboxes to load...")
        await page.wait_for_selector('.experts-modal-table__expert input[type="checkbox"]', timeout=10000)
        await page.wait_for_timeout(wait_time('modal_render'))

        # Check all experts first (to ensure a clean state)
        logger.info("Checking all experts first...")
        select_all = page.locator('#experts-modal-select-all')
        await select_all.check()
        await page.wait_for_timeout(wait_time('state_update'))
        
        # Then uncheck all experts
        logger.info("Unchecking all experts...")
        await select_all.uncheck()
        await page.wait_for_timeout(wait_time('state_update'))

        # Select specific experts using their IDs (like in the JavaScript version)
        logger.info("Selecting specific experts...")
        expert_ids = ['22', '1139']  # You can modify these IDs as needed
        
        for expert_id in expert_ids:
            try:
                checkbox_selector = f'#experts-modal-select-expert-{expert_id}'
                label_selector = f'label[for="experts-modal-select-expert-{expert_id}"]'
                row_selector = f'#experts-modal-table-row-{expert_id}'
                
                # Check if checkbox exists
                checkbox = page.locator(checkbox_selector)
                if await checkbox.count() == 0:
                    logger.error(f"Checkbox not found for expert {expert_id}")
                    continue
                
                # Scroll the row into view
                row = page.locator(row_selector)
                if await row.count() > 0:
                    await row.scroll_into_view_if_needed()
                    await page.wait_for_timeout(wait_time('scroll'))
                
                # Check current state
                is_initially_checked = await checkbox.is_checked()
                logger.debug(f"Expert {expert_id} initial state: {'checked' if is_initially_checked else 'unchecked'}")
                
                if not is_initially_checked:
                    success = False
                    
                    # Method 1: Click the label (most reliable for custom checkboxes)
                    try:
                        logger.debug(f"Trying to click label for expert {expert_id}")
                        label = page.locator(label_selector)
                        if await label.count() > 0:
                            await label.click()
                            await page.wait_for_timeout(wait_time('click'))
                            success = await checkbox.is_checked()
                            if success:
                                logger.debug(f"Successfully selected via label click")
                    except Exception as e:
                        logger.debug(f"Label click failed: {e}")
                    
                    # Method 2: Use JavaScript to directly check the checkbox
                    if not success:
                        try:
                            logger.debug(f"Trying JavaScript for expert {expert_id}")
                            await page.evaluate(f"document.querySelector('{checkbox_selector}').checked = true")
                            await page.evaluate(f"document.querySelector('{checkbox_selector}').dispatchEvent(new Event('change', {{ bubbles: true }}))")
                            await page.wait_for_timeout(wait_time('click'))
                            success = await checkbox.is_checked()
                            if success:
                                logger.debug(f"Successfully selected via JavaScript")
                        except Exception as e:
                            logger.debug(f"JavaScript method failed: {e}")
                    
                    # Method 3: Click the checkbox container div
                    if not success:
                        try:
                            logger.debug(f"Trying to click checkbox container for expert {expert_id}")
                            container = page.locator(f'{row_selector} .experts-modal-table__row-item--checkbox div')
                            if await container.count() > 0:
                                await container.first.click()
                                await page.wait_for_timeout(wait_time('click'))
                                success = await checkbox.is_checked()
                                if success:
                                    logger.debug(f"Successfully selected via container click")
                        except Exception as e:
                            logger.debug(f"Container click failed: {e}")
                    
                    # Method 4: Force click on checkbox
                    if not success:
                        try:
                            logger.debug(f"Trying force click for expert {expert_id}")
                            await checkbox.click(force=True)
                            await page.wait_for_timeout(wait_time('click'))
                            success = await checkbox.is_checked()
                            if success:
                                logger.debug(f"Successfully selected via force click")
                        except Exception as e:
                            logger.debug(f"Force click failed: {e}")
                    
                    # Method 5: Click on the row itself
                    if not success:
                        try:
                            logger.debug(f"Trying row click for expert {expert_id}")
                            await row.click()
                            await page.wait_for_timeout(wait_time('click'))
                            success = await checkbox.is_checked()
                            if success:
                                logger.debug(f"Successfully selected via row click")
                        except Exception as e:
                            logger.debug(f"Row click failed: {e}")
                    
                    # Final verification
                    if await checkbox.is_checked():
                        logger.info(f"✓ Successfully selected expert with ID: {expert_id}")
                    else:
                        logger.error(f"✗ Failed to select expert {expert_id} after all attempts")
                else:
                    logger.info(f"✓ Expert {expert_id} was already selected")
                    
            except Exception as e:
                logger.error(f"Unexpected error with expert {expert_id}: {e}")
            
        logger.info("Taking screenshot of expert selection...")
        screenshot_path = self.output_dir / 'screenshots' / 'expert_selection.png'
        await page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")

        if wait_time('verification') > 0:
            logger.info(f"Pausing for {wait_time('verification')/1000:.1f} seconds for verification...")
            await page.wait_for_timeout(wait_time('verification'))

        logger.info("Applying expert selection...")
        # Try multiple methods to click Apply
        try:
            # Method 1: Text selector
            await page.click('text="Apply"', timeout=5000)
        except Exception:
            try:
                # Method 2: Button with Apply text
                apply_button = page.locator('button:has-text("Apply")')
                await apply_button.click()
            except Exception:
                # Method 3: Force click
                await page.locator('text="Apply"').click(force=True)

        # Wait for modal to close
        try:
            await expect(experts_modal).not_to_be_visible(timeout=10000)
            logger.info("Expert selection applied and modal closed.")
        except Exception:
            logger.warning("Modal may still be visible, but continuing...")
        
        # Give a moment for the page to update
        await page.wait_for_timeout(wait_time('page_update'))
        logger.info("Expert selection complete.")

    async def scrape_rankings_table(self, page: Page) -> None:
        """Scrape the rankings table and save to CSV"""
        logger.info("Starting to scrape rankings table...")
        
        try:
            # Wait for the table to be present
            await page.wait_for_selector('#ranking-table', timeout=10000)
            logger.info("Rankings table found.")
            
            # Extract table data using page.evaluate
            table_data = await page.evaluate('''() => {
                const rows = [];
                const table = document.querySelector('#ranking-table');
                if (!table) return rows;
                
                const tbody = table.querySelector('tbody');
                if (!tbody) return rows;
                
                const playerRows = tbody.querySelectorAll('tr.player-row');
                let currentTier = '';
                
                // Iterate through all rows to capture tiers and players
                const allRows = tbody.querySelectorAll('tr');
                for (const row of allRows) {
                    if (row.classList.contains('tier-row')) {
                        // Extract tier information
                        const tierCell = row.querySelector('.sticky-cell-one');
                        if (tierCell) {
                            currentTier = tierCell.textContent.trim();
                        }
                    } else if (row.classList.contains('player-row')) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 9) {
                            // Extract player information
                            const playerCell = row.querySelector('.player-cell__td');
                            const playerLink = playerCell ? playerCell.querySelector('.player-cell-name') : null;
                            const teamSpan = playerCell ? playerCell.querySelector('.player-cell-team') : null;
                            
                            // Check for movement indicators
                            const riserIcon = playerCell ? playerCell.querySelector('.ranking-riser') : null;
                            const fallerIcon = playerCell ? playerCell.querySelector('.ranking-faller') : null;
                            let movement = '';
                            if (riserIcon) {
                                const tooltip = riserIcon.parentElement.getAttribute('data-tooltip');
                                movement = tooltip || 'Rising';
                            } else if (fallerIcon) {
                                const tooltip = fallerIcon.parentElement.getAttribute('data-tooltip');
                                movement = tooltip || 'Falling';
                            }
                            
                            // Extract BYE week (cells[4])
                            const bye = cells[4] ? cells[4].textContent.trim() : '';
                            
                            // Extract SOS (cells[5]) - get only the first sr-only span for star rating
                            let sos = '';
                            let sosTooltip = '';
                            if (cells[5]) {
                                const sosDiv = cells[5].querySelector('.template-stars');
                                if (sosDiv) {
                                    sosTooltip = sosDiv.getAttribute('data-tooltip') || '';
                                    // Get just the first sr-only span text which contains "X out of 5 stars"
                                    const firstSrOnly = sosDiv.querySelector('.sr-only');
                                    sos = firstSrOnly ? firstSrOnly.textContent.trim() : '';
                                }
                            }
                            
                            // Extract ECR VS ADP (cells[6])
                            const ecrVsAdpDiv = cells[6] ? cells[6].querySelector('.ecr-vs-adp-wrap') : null;
                            const ecrVsAdp = ecrVsAdpDiv ? ecrVsAdpDiv.textContent.trim() : '';
                            const ecrVsAdpTooltip = ecrVsAdpDiv ? ecrVsAdpDiv.getAttribute('data-tooltip') : '';
                            
                            // Extract AVG. DIFF (cells[7])
                            let avgDiff = '';
                            let avgDiffTooltip = '';
                            if (cells[7]) {
                                const avgDiffSpan = cells[7].querySelector('span[data-tooltip]');
                                if (avgDiffSpan) {
                                    avgDiff = avgDiffSpan.textContent.trim();
                                    avgDiffTooltip = avgDiffSpan.getAttribute('data-tooltip') || '';
                                }
                            }
                            
                            // Extract % OVER (cells[8])
                            let percentOver = '';
                            let percentOverTooltip = '';
                            if (cells[8]) {
                                const percentOverSpan = cells[8].querySelector('span[data-tooltip]');
                                if (percentOverSpan) {
                                    percentOver = percentOverSpan.textContent.trim();
                                    percentOverTooltip = percentOverSpan.getAttribute('data-tooltip') || '';
                                }
                            }
                            
                            rows.push({
                                tier: currentTier,
                                rank: cells[0] ? cells[0].textContent.trim() : '',
                                playerName: playerLink ? playerLink.textContent.trim() : '',
                                playerId: playerLink ? playerLink.getAttribute('fp-player-id') : '',
                                team: teamSpan ? teamSpan.textContent.replace(/[()]/g, '').trim() : '',
                                position: cells[3] ? cells[3].textContent.trim() : '',
                                bye: bye,
                                sos: sos,
                                sosTooltip: sosTooltip,
                                ecrVsAdp: ecrVsAdp,
                                ecrVsAdpTooltip: ecrVsAdpTooltip,
                                avgDiff: avgDiff,
                                avgDiffTooltip: avgDiffTooltip,
                                percentOver: percentOver,
                                percentOverTooltip: percentOverTooltip,
                                movement: movement
                            });
                        }
                    }
                }
                
                return rows;
            }''')
            
            logger.info(f"Extracted {len(table_data)} player rankings.")
            
            if table_data:
                # Save to CSV
                csv_path = self.output_dir / 'rankings.csv'
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    if table_data:
                        fieldnames = ['tier', 'rank', 'playerName', 'playerId', 'team', 'position', 
                                    'bye', 'sos', 'sosTooltip', 'ecrVsAdp', 'ecrVsAdpTooltip', 
                                    'avgDiff', 'avgDiffTooltip', 'percentOver', 'percentOverTooltip', 'movement']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(table_data)
                logger.info(f"Rankings saved to CSV: {csv_path}")
                
                # Also save to JSON for easier processing
                json_path = self.output_dir / 'rankings.json'
                with open(json_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(table_data, jsonfile, indent=2)
                logger.info(f"Rankings saved to JSON: {json_path}")
                
                # Take a screenshot of the rankings table
                screenshot_path = self.output_dir / 'screenshots' / 'rankings_table.png'
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Screenshot of rankings saved to {screenshot_path}")
                
                # Print first few entries as confirmation
                logger.info("Sample of scraped data:")
                for i, player in enumerate(table_data[:5]):
                    logger.info(f"  {player['rank']}. {player['playerName']} ({player['team']}) - {player['position']} - BYE: {player['bye']} - SOS: {player['sos']} - ECR vs ADP: {player['ecrVsAdp']}")
            else:
                logger.warning("No data extracted from the rankings table.")
                
        except Exception as e:
            logger.error(f"Error scraping rankings table: {e}")
            # Take a screenshot for debugging
            error_screenshot = self.output_dir / 'screenshots' / 'error_state.png'
            await page.screenshot(path=error_screenshot, full_page=True)
            logger.info(f"Error screenshot saved to {error_screenshot}")


async def main():
    """Entry point"""
    scraper = FantasyProsNewScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())

