# FantasyPros Scraper Makefile
# Convenient commands for development and usage

.PHONY: help setup test scrape analyze clean update shell venv install

# Python interpreter
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PYTHON_VENV := $(VENV_BIN)/python
PIP_VENV := $(VENV_BIN)/pip

# Default target
help:
	@echo "FantasyPros Scraper - Available Commands:"
	@echo "========================================"
	@echo "make setup     - Complete first-time setup"
	@echo "make test      - Run all tests"
	@echo "make scrape    - Run the scraper"
	@echo "make analyze   - Analyze latest rankings"
	@echo "make clean     - Clean output files"
	@echo "make update    - Update dependencies"
	@echo "make shell     - Open Python shell with imports"
	@echo ""
	@echo "Quick start: make setup && make test"

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv $(VENV)
	@echo "✓ Virtual environment created"

# Install dependencies
install: venv
	@echo "Installing dependencies..."
	@$(PIP_VENV) install --upgrade pip
	@$(PIP_VENV) install -r requirements.txt
	@$(PYTHON_VENV) -m playwright install chromium
	@echo "✓ Dependencies installed"

# Complete setup
setup: install
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		if [ -f env.example ]; then \
			cp env.example .env; \
			echo "✓ Created .env file from env.example"; \
			echo ""; \
			echo "⚠️  IMPORTANT: Edit .env with your FantasyPros credentials"; \
			echo "   Email and password are required for the scraper to work"; \
		fi \
	else \
		echo "✓ .env file already exists"; \
	fi
	@mkdir -p output
	@echo "✓ Output directory created"
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env with your credentials"
	@echo "2. Run: make test"
	@echo "3. Run: make scrape"

# Run tests
test:
	@echo "Running tests..."
	@$(PYTHON_VENV) test_scraper.py

# Run scraper
scrape:
	@if [ ! -f .env ]; then \
		echo "❌ No .env file found!"; \
		echo "Run: make setup"; \
		exit 1; \
	fi
	@echo "Starting scraper..."
	@$(PYTHON_VENV) scraper.py

# Run scraper in headless mode
scrape-headless:
	@if [ ! -f .env ]; then \
		echo "❌ No .env file found!"; \
		echo "Run: make setup"; \
		exit 1; \
	fi
	@echo "Starting scraper in headless mode..."
	@HEADLESS=true $(PYTHON_VENV) scraper.py

# Analyze rankings
analyze:
	@echo "Analyzing rankings..."
	@$(PYTHON_VENV) analyze_rankings.py

# Analyze with options
analyze-top20:
	@$(PYTHON_VENV) analyze_rankings.py --top 20

analyze-top50:
	@$(PYTHON_VENV) analyze_rankings.py --top 50

analyze-export:
	@$(PYTHON_VENV) analyze_rankings.py --export

# Clean output files
clean:
	@echo "Cleaning output files..."
	@rm -f output/*.csv output/*.json output/*.xlsx output/*.txt output/*.log
	@rm -rf output/screenshots/*.png
	@echo "✓ Output files cleaned"

# Clean everything (including venv)
clean-all: clean
	@echo "Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "✓ Virtual environment removed"

# Update dependencies
update: venv
	@echo "Updating dependencies..."
	@$(PIP_VENV) install --upgrade pip
	@$(PIP_VENV) install --upgrade -r requirements.txt
	@$(PYTHON_VENV) -m playwright install chromium
	@echo "✓ Dependencies updated"

# Open Python shell with imports
shell:
	@$(PYTHON_VENV) -i -c "import pandas as pd; import json; from pathlib import Path; from scraper import FantasyProsScraper; from utils import *; import asyncio; print('\n🐍 Python shell with FantasyPros scraper loaded\nAvailable: pd, json, Path, FantasyProsScraper, utils functions\nExample: df = load_latest_rankings()\n')"

# Check environment
check-env:
	@echo "Checking environment..."
	@echo "Python: $$($(PYTHON) --version)"
	@if [ -d $(VENV) ]; then \
		echo "Virtual environment: ✓ Found"; \
	else \
		echo "Virtual environment: ✗ Not found (run: make setup)"; \
	fi
	@if [ -f .env ]; then \
		echo ".env file: ✓ Found"; \
		if grep -q "your_email@example.com" .env; then \
			echo "⚠️  Warning: .env contains example values - please update!"; \
		fi \
	else \
		echo ".env file: ✗ Not found (run: make setup)"; \
	fi

# Run scraper with debug logging
debug:
	@echo "Running scraper with debug logging..."
	@$(PYTHON_VENV) -u scraper.py 2>&1 | tee "output/scraper_$$(date +%Y%m%d_%H%M%S).log"

# Quick commands for common player lookups
player:
	@read -p "Enter player name: " player; \
	$(PYTHON_VENV) analyze_rankings.py --player "$$player"

# Development helpers
.PHONY: lint format

# Run linting (requires installation of flake8)
lint:
	@$(PIP_VENV) install -q flake8
	@$(VENV_BIN)/flake8 *.py --max-line-length=120 --exclude=venv

# Format code (requires installation of black)
format:
	@$(PIP_VENV) install -q black
	@$(VENV_BIN)/black *.py --line-length=120 --exclude=venv 