#!/usr/bin/env python3
"""
Test script for FantasyPros Scraper
Verifies setup and basic functionality
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import colorlog

# Setup logging
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s: %(message)s',
    log_colors={'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red'}
))
logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel('INFO')


def test_environment():
    """Test environment setup"""
    logger.info("Testing environment setup...")
    
    # Check if .env exists
    if not Path('.env').exists():
        logger.error(".env file not found. Run python setup.py first")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check required variables
    email = os.getenv('FANTASYPROS_EMAIL')
    password = os.getenv('FANTASYPROS_PASSWORD')
    
    if not email or email == 'your_email@example.com':
        logger.error("FANTASYPROS_EMAIL not configured in .env")
        return False
    
    if not password or password == 'your_password':
        logger.error("FANTASYPROS_PASSWORD not configured in .env")
        return False
    
    logger.info("✅ Environment variables loaded successfully")
    return True


def test_imports():
    """Test all required imports"""
    logger.info("Testing imports...")
    
    try:
        import pandas
        import numpy
        import playwright
        import dotenv
        import colorlog
        import openpyxl
        logger.info("✅ All required packages imported successfully")
        return True
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Run: pip install -r requirements.txt")
        return False


async def test_playwright():
    """Test Playwright browser launch"""
    logger.info("Testing Playwright browser launch...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.google.com")
            title = await page.title()
            await browser.close()
            
            if "Google" in title:
                logger.info("✅ Playwright browser test successful")
                return True
            else:
                logger.error("Unexpected page title")
                return False
    except Exception as e:
        logger.error(f"Playwright test failed: {e}")
        logger.error("Run: playwright install chromium")
        return False


async def test_fantasypros_access():
    """Test access to FantasyPros website"""
    logger.info("Testing FantasyPros website access...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set a realistic user agent
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = await page.goto(
                "https://www.fantasypros.com/nfl/rankings/half-point-ppr-cheatsheets.php",
                wait_until="domcontentloaded",
                timeout=30000
            )
            
            await browser.close()
            
            if response and response.status == 200:
                logger.info("✅ FantasyPros website accessible")
                return True
            else:
                logger.error(f"Failed to access FantasyPros. Status: {response.status if response else 'No response'}")
                return False
    except Exception as e:
        logger.error(f"FantasyPros access test failed: {e}")
        return False


def test_output_directory():
    """Test output directory creation"""
    logger.info("Testing output directory...")
    
    output_dir = Path("output")
    if not output_dir.exists():
        output_dir.mkdir()
    
    if output_dir.exists() and output_dir.is_dir():
        logger.info("✅ Output directory ready")
        return True
    else:
        logger.error("Failed to create output directory")
        return False


async def run_tests():
    """Run all tests"""
    print("🧪 FantasyPros Scraper Test Suite")
    print("=" * 40)
    
    tests = [
        ("Environment Setup", test_environment),
        ("Python Imports", test_imports),
        ("Output Directory", test_output_directory),
        ("Playwright Browser", test_playwright),
        ("FantasyPros Access", test_fantasypros_access),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Tests Passed: {passed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ All tests passed! The scraper is ready to use.")
        print("\nRun the scraper with: python scraper.py")
    else:
        print(f"\n❌ {failed} test(s) failed. Please fix the issues above.")
        return False
    
    return True


def main():
    """Main entry point"""
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 