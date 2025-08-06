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

# Set log level based on DEBUG environment variable
if os.getenv('DEBUG', 'false').lower() == 'true':
    logger.setLevel('DEBUG')
else:
    logger.setLevel('DEBUG')  # Temporarily force DEBUG level for troubleshooting


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
        self.login_url = f"{self.base_url}/accounts/signin/"
        self.post_login_url = f"{self.base_url}/?signedin"
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
        """Login to FantasyPros using the dedicated signin page"""
        try:
            logger.info("Navigating to FantasyPros login page...")
            
            # Go directly to the signin page
            await page.goto(self.login_url, wait_until="domcontentloaded", timeout=self.timeout)
            await page.wait_for_timeout(2000)  # Let page fully load
            
            logger.info("Filling login credentials...")
            
            # Only screenshot login page if DEBUG is explicitly enabled
            # (removed automatic screenshot since login is working)
            
            # Debug: List all input fields on the page
            all_inputs = await page.locator("input").all()
            logger.info(f"Found {len(all_inputs)} input fields on login page")
            
            for i, input_elem in enumerate(all_inputs):
                try:
                    input_type = await input_elem.get_attribute("type") or "text"
                    input_name = await input_elem.get_attribute("name") or "no-name"
                    input_id = await input_elem.get_attribute("id") or "no-id"
                    input_placeholder = await input_elem.get_attribute("placeholder") or "no-placeholder"
                    logger.debug(f"Input {i}: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
                except:
                    logger.debug(f"Input {i}: Could not read attributes")
            
            # Fill login form - try multiple possible selectors
            email_filled = False
            password_filled = False
            
            # Try common email field selectors
            email_selectors = [
                "input[name='email']", "input[type='email']", "#email", "#id_email",
                "input[name='username']", "input[placeholder*='email' i]", 
                "input[placeholder*='Email' i]", "input[autocomplete='email']"
            ]
            
            for email_selector in email_selectors:
                try:
                    if await page.locator(email_selector).count() > 0:
                        await page.fill(email_selector, self.email)
                        email_filled = True
                        logger.info(f"✅ Email filled using selector: {email_selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to fill email with {email_selector}: {e}")
                    continue
            
            # Try common password field selectors
            password_selectors = [
                "input[name='password']", "input[type='password']", "#password", "#id_password",
                "input[placeholder*='password' i]", "input[placeholder*='Password' i]",
                "input[autocomplete='current-password']", "input[autocomplete='password']"
            ]
            
            for password_selector in password_selectors:
                try:
                    if await page.locator(password_selector).count() > 0:
                        await page.fill(password_selector, self.password)
                        password_filled = True
                        logger.info(f"✅ Password filled using selector: {password_selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to fill password with {password_selector}: {e}")
                    continue
            
            if not email_filled or not password_filled:
                # Take screenshot of failure (always, for debugging)
                (self.output_dir / 'screenshots').mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = self.output_dir / 'screenshots' / f"login_failure_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                logger.error(f"Could not find email or password fields on login page - screenshot saved to {screenshot_path}")
                
                # Try to find any form on the page
                forms = await page.locator("form").all()
                logger.info(f"Found {len(forms)} forms on the page")
                
                if not email_filled:
                    logger.error("❌ Email field not found - tried selectors: " + ", ".join(email_selectors))
                if not password_filled:
                    logger.error("❌ Password field not found - tried selectors: " + ", ".join(password_selectors))
                
                return False
            
            # Submit the form - try multiple submit methods
            submitted = False
            for submit_selector in ["button[type='submit']", "input[type='submit']", "button:has-text('Sign In')", "button:has-text('Login')"]:
                try:
                    if await page.locator(submit_selector).count() > 0:
                        await page.click(submit_selector)
                        submitted = True
                        logger.debug(f"Form submitted using selector: {submit_selector}")
                        break
                except:
                    continue
            
            if not submitted:
                logger.error("Could not find submit button on login page")
                return False
            
            logger.info("Login form submitted, waiting for redirect...")
            
            # Wait for successful login - check that we're no longer on signin/login page
            try:
                await page.wait_for_url(lambda url: "signin" not in url and "login" not in url, timeout=15000)
                logger.info("Successfully logged in and redirected away from login page")
            except:
                # If we're still on login page, check for errors
                current_url = page.url
                if "signin" in current_url or "login" in current_url:
                    # Check for error messages
                    error_selectors = [
                        ".error", ".alert-danger", ".form-error", 
                        "[class*='error']", "[class*='invalid']"
                    ]
                    for selector in error_selectors:
                        if await page.locator(selector).count() > 0:
                            error_text = await page.locator(selector).first.inner_text()
                            logger.error(f"Login error detected: {error_text}")
                            break
                    
                    # Check for CAPTCHA
                    captcha_selectors = ["[class*='captcha']", "[class*='recaptcha']", "#captcha"]
                    for selector in captcha_selectors:
                        if await page.locator(selector).count() > 0:
                            logger.error("CAPTCHA detected - manual intervention may be required")
                            if not self.headless:
                                logger.info("Running in non-headless mode - please solve CAPTCHA manually")
                                await page.wait_for_timeout(30000)  # Give user time to solve
                            break
                    
                    logger.error("Still on login page - login likely failed")
                    return False
                else:
                    logger.info(f"Login appears successful (current URL: {current_url})")
            
            # After successful login, explicitly navigate to the rankings page
            # This ensures we're on the correct page regardless of post-login redirects
            current_url = page.url
            logger.info(f"Post-login URL: {current_url}")
            logger.info(f"Navigating to rankings page: {self.rankings_url}")
            await page.goto(self.rankings_url, wait_until="domcontentloaded", timeout=self.timeout)
            await page.wait_for_timeout(2000)  # Allow page to fully load
            
            logger.info("Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def get_available_experts(self, page: Page) -> List[str]:
        """Get list of all available experts from the modal"""
        logger.info("Fetching available experts...")
        
        # Open expert selection modal
        await page.locator("button[aria-label='Open experts modal']").click()
        
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
        
        # Close modal - try multiple methods
        try:
            # Try the close button first
            await page.click("button.experts-modal__header-close", timeout=5000)
        except:
            # If that fails, try clicking outside the modal or press Escape
            try:
                await page.keyboard.press("Escape")
            except:
                pass
        
        # Wait for modal to close
        await expect(experts_modal).not_to_be_visible()
        await page.wait_for_timeout(1000)
        
        logger.info(f"Found {len(experts)} available experts")
        logger.debug(f"First few experts: {experts[:5]}")  # Show first 5 expert names
        return experts
    
    async def select_expert_pair(self, page: Page, expert1: str, expert2: str) -> bool:
        """Select exactly two experts in the modal"""
        try:
            experts_modal = page.locator(".experts-modal")
            
            # Check if modal is already open
            if await experts_modal.is_visible():
                logger.debug("Experts modal already open, closing it first")
                try:
                    # Try clicking the close button first
                    close_button = page.locator("button.experts-modal__header-close")
                    if await close_button.is_visible():
                        await close_button.click()
                    else:
                        # Fallback to Escape key
                        await page.keyboard.press("Escape")
                    
                    # Wait for modal to fully disappear
                    await expect(experts_modal).not_to_be_visible(timeout=5000)
                    await page.wait_for_timeout(1000)  # Extra time for cleanup
                except Exception as e:
                    logger.debug(f"Error closing modal: {e}")
                    # Force close by clicking outside modal area
                    try:
                        await page.click("body", position={"x": 50, "y": 50})
                        await page.wait_for_timeout(1000)
                    except:
                        pass
            
            # Open expert selection modal
            await page.locator("button[aria-label='Open experts modal']").click()
            await expect(experts_modal).to_be_visible()
            await page.wait_for_timeout(1000)  # Let modal fully load
            
            # Step 1: Handle "Select all experts" checkbox - uncheck it if checked
            select_all_checkbox = page.locator("#experts-modal-select-all")
            if await select_all_checkbox.count() > 0:
                is_checked = await select_all_checkbox.is_checked()
                if is_checked:
                    logger.debug("Unchecking 'Select all experts' checkbox")
                    await select_all_checkbox.uncheck()
                    await page.wait_for_timeout(500)  # Wait for state to update
                else:
                    logger.debug("'Select all experts' checkbox is already unchecked")
            else:
                logger.debug("'Select all experts' checkbox not found")
            
            # Step 2: Clear all individual expert selections (redundant safety step)
            # Try to find and click "Clear All" button if it exists
            try:
                clear_button = experts_modal.get_by_role("button", name="Clear All")
                if await clear_button.is_visible():
                    await clear_button.click()
                    await page.wait_for_timeout(500)
                    logger.debug("Clicked 'Clear All' button")
            except:
                logger.debug("'Clear All' button not found or not clickable")
            
            # Step 3: Find and select the two specific experts
            selected_count = 0
            expert_rows = await page.locator(".experts-modal-table__expert").all()
            logger.info(f"Found {len(expert_rows)} expert rows in modal")
            
            # Debug: Let's see what we're actually looking for
            logger.info(f"Looking for experts: '{expert1}' and '{expert2}'")
            
            for i, row in enumerate(expert_rows):
                try:
                    name_element = row.locator(".yearbook-block__title-link")
                    if await name_element.count() > 0:
                        row_expert_name = await name_element.inner_text()
                        site_element = row.locator(".yearbook-block__description-text")
                        site_name = await site_element.inner_text() if await site_element.count() > 0 else ""
                        full_name = f"{row_expert_name.strip()} ({site_name.strip()})" if site_name else row_expert_name.strip()
                        
                        # Debug: Log all expert names we find
                        if i < 10:  # Only log first 10 to avoid spam
                            logger.debug(f"Row {i}: Found expert '{full_name}'")
                        
                        if full_name in [expert1, expert2]:
                            logger.info(f"🎯 MATCH FOUND: '{full_name}' matches one of our targets")
                            
                            # Try multiple checkbox selectors
                            checkbox_selectors = [
                                "input.custom-checkbox-input[type='checkbox']",
                                "input[type='checkbox']",
                                ".custom-checkbox-input",
                                "input"
                            ]
                            
                            checkbox_clicked = False
                            for selector in checkbox_selectors:
                                try:
                                    checkbox = row.locator(selector)
                                    checkbox_count = await checkbox.count()
                                    logger.debug(f"  Trying selector '{selector}': found {checkbox_count} elements")
                                    
                                    if checkbox_count > 0:
                                        # Check if it's actually a checkbox
                                        first_checkbox = checkbox.first
                                        input_type = await first_checkbox.get_attribute("type")
                                        input_id = await first_checkbox.get_attribute("id")
                                        input_class = await first_checkbox.get_attribute("class")
                                        
                                        logger.debug(f"    Element details: type='{input_type}', id='{input_id}', class='{input_class}'")
                                        
                                        if input_type == "checkbox":
                                            is_checked_before = await first_checkbox.is_checked()
                                            logger.debug(f"    Checkbox state before click: {is_checked_before}")
                                            
                                            # Try clicking the checkbox
                                            await first_checkbox.check()
                                            await page.wait_for_timeout(500)  # Wait for state change
                                            
                                            is_checked_after = await first_checkbox.is_checked()
                                            logger.debug(f"    Checkbox state after click: {is_checked_after}")
                                            
                                            if is_checked_after:
                                                selected_count += 1
                                                checkbox_clicked = True
                                                logger.info(f"✅ Successfully selected expert: {full_name}")
                                                break
                                            else:
                                                logger.warning(f"    Checkbox click didn't work for {full_name}")
                                        else:
                                            logger.debug(f"    Element is not a checkbox (type='{input_type}')")
                                except Exception as e:
                                    logger.debug(f"    Error with selector '{selector}': {e}")
                                    continue
                            
                            if not checkbox_clicked:
                                logger.error(f"❌ Failed to select expert: {full_name} - no working checkbox found")
                                
                                # Debug: Let's see the full HTML of this row
                                try:
                                    row_html = await row.inner_html()
                                    logger.debug(f"Row HTML for {full_name}: {row_html[:500]}...")  # First 500 chars
                                except Exception as e:
                                    logger.debug(f"Could not get row HTML: {e}")
                            
                            if selected_count == 2:
                                break
                        
                except Exception as e:
                    logger.debug(f"Error processing expert row {i}: {e}")
                    continue
            
            if selected_count != 2:
                logger.error(f"Could not select both experts. Selected: {selected_count}/2")
                logger.error(f"Looking for: {expert1}, {expert2}")
                
                # Take a screenshot for debugging
                try:
                    (self.output_dir / 'screenshots').mkdir(exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = self.output_dir / 'screenshots' / f"expert_selection_failure_{timestamp}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.error(f"Expert selection failure screenshot saved to {screenshot_path}")
                except:
                    pass
                
                # Close modal and return failure
                try:
                    await page.click("button.experts-modal__header-close")
                except:
                    await page.keyboard.press("Escape")
                return False
            
            # Step 4: Apply the selection using the correct button selector
            logger.debug("Applying expert selection...")
            
            # Try the primary Apply button first (based on your HTML)
            apply_button_selectors = [
                "button.fp-cta-button.fp-cta-button__primary:has-text('Apply')",
                "button:has-text('Apply')",
                "button.fp-cta-button:has-text('Apply')",
                # Fallback to the old selector
                experts_modal.get_by_role("button", name="Save My Experts")
            ]
            
            applied = False
            for selector in apply_button_selectors[:-1]:  # Try CSS selectors first
                try:
                    apply_button = page.locator(selector)
                    if await apply_button.count() > 0 and await apply_button.is_visible():
                        await apply_button.click()
                        applied = True
                        logger.debug(f"✅ Applied selection using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to click Apply button with selector {selector}: {e}")
                    continue
            
            # Try the role-based selector as fallback
            if not applied:
                try:
                    save_button = apply_button_selectors[-1]  # The locator object
                    if await save_button.is_visible():
                        await save_button.click()
                        applied = True
                        logger.debug("✅ Applied selection using 'Save My Experts' button")
                except Exception as e:
                    logger.debug(f"Failed to click 'Save My Experts' button: {e}")
            
            if not applied:
                logger.error("Could not find or click Apply/Save button")
                return False
            
            # Wait for modal to close and rankings to update
            try:
                await expect(experts_modal).not_to_be_visible(timeout=10000)
                logger.debug("Modal closed automatically after applying selection")
            except:
                # If modal doesn't close automatically, force close it
                logger.debug("Modal didn't close automatically, forcing close")
                try:
                    close_button = page.locator("button.experts-modal__header-close")
                    if await close_button.is_visible():
                        await close_button.click()
                    else:
                        await page.keyboard.press("Escape")
                    await expect(experts_modal).not_to_be_visible(timeout=5000)
                except Exception as e:
                    logger.debug(f"Error force-closing modal: {e}")
                    # Last resort - click outside
                    try:
                        await page.click("body", position={"x": 50, "y": 50})
                    except:
                        pass
            
            # Extra wait for page to stabilize and rankings to update
            await page.wait_for_timeout(self.delay + 1000)
            
            logger.info(f"✅ Successfully selected experts: {expert1} + {expert2}")
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
        specific_experts_raw = os.getenv('SPECIFIC_EXPERTS', '').strip()
        logger.debug(f"SPECIFIC_EXPERTS env var: '{specific_experts_raw}'")
        
        # Clean up environment variable - remove comments and whitespace
        if specific_experts_raw and not specific_experts_raw.startswith('#'):
            # Split by '#' to remove inline comments
            specific_experts = specific_experts_raw.split('#')[0].strip()
        else:
            specific_experts = ''
        
        logger.debug(f"Cleaned SPECIFIC_EXPERTS: '{specific_experts}'")
        logger.debug(f"Max experts to scrape: {self.max_experts}")
        
        if specific_experts:
            self.experts_list = [e.strip() for e in specific_experts.split(',') if e.strip() in available_experts]
            logger.info(f"Using {len(self.experts_list)} specific experts from environment")
        else:
            self.experts_list = available_experts[:self.max_experts]
            logger.info(f"Using first {len(self.experts_list)} experts from available list")
        
        logger.debug(f"Selected experts: {self.experts_list[:5]}...")  # Show first 5
        
        if len(self.experts_list) < 3:
            logger.error(f"Not enough valid experts specified. Got {len(self.experts_list)}, need at least 3")
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
                # Handle cookie consent first (on any page)
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=self.timeout)
                await self.handle_cookie_consent(page)
                
                # Login is required for Pick Experts feature
                logger.info("Logging in to FantasyPros...")
                if not await self.login(page):
                    logger.error("Login failed, cannot proceed")
                    return
                
                # Wait for page to fully load - use domcontentloaded instead of networkidle
                # (networkidle can timeout on pages with ongoing background requests)
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as e:
                    logger.warning(f"Networkidle timeout (normal for dynamic pages): {e}")
                    logger.info("Continuing with domcontentloaded state...")
                
                await page.wait_for_timeout(3000)  # Give extra time for dynamic content
                
                # Verify we can access the Pick Experts feature
                pick_experts_button = page.locator("button[aria-label='Open experts modal']")
                if await pick_experts_button.count() == 0:
                    logger.error("Pick Experts button not found - login may have failed or feature unavailable")
                    
                    # Take screenshot of the issue
                    try:
                        (self.output_dir / 'screenshots').mkdir(exist_ok=True)
                        error_screenshot = self.output_dir / 'screenshots' / f"no_pick_experts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        await page.screenshot(path=error_screenshot)
                        logger.error(f"💾 Pick Experts missing screenshot saved to {error_screenshot}")
                    except:
                        pass
                    
                    return
                else:
                    logger.info("✅ Pick Experts feature is accessible")
                
                # Start scraping
                await self.scrape_all_experts(page)
                
                # Save results
                if self.expert_rankings:
                    self.save_results()
                else:
                    logger.warning("No rankings were scraped")
                
            except Exception as e:
                logger.error(f"Scraping failed: {e}")
                
                # Always take screenshot on errors for debugging
                try:
                    (self.output_dir / 'screenshots').mkdir(exist_ok=True)
                    error_screenshot = self.output_dir / 'screenshots' / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=error_screenshot)
                    logger.error(f"💾 Error screenshot saved to {error_screenshot}")
                except Exception as screenshot_error:
                    logger.debug(f"Could not save error screenshot: {screenshot_error}")
                
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