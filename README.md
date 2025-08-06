# FantasyPros Expert Rankings Scraper

A sophisticated web scraper that extracts individual expert rankings from FantasyPros using a strategic pairing algorithm to overcome the 2-expert selection limitation.

## How It Works

FantasyPros only allows selecting 2 experts at a time to view consensus rankings. This scraper uses an algebraic deduction method to calculate individual expert rankings:

1. **Baseline Establishment**: Selects 3 experts (A, B, C) and gets consensus rankings for pairs AB, AC, and BC
2. **Algebraic Deduction**: Uses formulas to calculate individual rankings:
   - `rank_A = avg(A,B) + avg(A,C) - avg(B,C)`
   - `rank_B = 2 * avg(A,B) - rank_A`
   - `rank_C = 2 * avg(A,C) - rank_A`
3. **Remaining Experts**: Uses expert A as baseline to deduce all other experts

## Features

- 🔐 Secure credential management via environment variables
- 🎯 Strategic pairing algorithm for individual ranking deduction
- 📊 Multiple output formats (JSON, CSV, Excel)
- 🖼️ Optional screenshot capture for debugging
- 🎨 Colored console logging for better visibility
- ⚡ Asynchronous scraping with Playwright
- 🛡️ Robust error handling and recovery
- 📈 Statistical analysis (average rank, standard deviation)

## Prerequisites

- Python 3.8 or higher
- Chrome/Chromium browser (automatically installed by Playwright)
- **FantasyPros account** (free registration required at [fantasypros.com](https://www.fantasypros.com))

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fantasypros-scraper.git
cd fantasypros-scraper
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your credentials
```

## Configuration

Edit the `.env` file with your settings:

```env
# Required: FantasyPros Credentials (login required for Pick Experts feature)
FANTASYPROS_EMAIL=your_email@example.com
FANTASYPROS_PASSWORD=your_password

# Optional: Scraping Configuration
HEADLESS=false                    # Run browser in headless mode
TIMEOUT=60000                     # Page load timeout in milliseconds
DELAY_BETWEEN_REQUESTS=2000       # Delay between requests in milliseconds

# Optional: Output Configuration
OUTPUT_DIR=output                 # Directory for output files
SAVE_SCREENSHOTS=false           # Save screenshots during scraping

# Optional: Expert Selection
MAX_EXPERTS_TO_SCRAPE=50         # Maximum number of experts to scrape
SPECIFIC_EXPERTS=                # Comma-separated list of specific experts
```

## Usage

### Quick Start with Convenience Scripts

**Option 1: Using the Makefile (Unix/Mac)**
```bash
make setup          # Complete first-time setup
make test           # Run tests to verify setup
make scrape         # Run the scraper
make analyze        # Analyze results
make help           # Show all available commands
```

**Option 2: Using Python Manager (All platforms)**
```bash
python manage.py setup         # Complete first-time setup
python manage.py test          # Run tests to verify setup
python manage.py scrape        # Run the scraper
python manage.py analyze       # Analyze results
python manage.py help          # Show all available commands
```

**Option 3: Direct Python Commands**
```bash
python setup.py     # Interactive setup script
python scraper.py   # Run scraper directly
```

### Advanced Usage

1. **Scrape specific experts only**:
   ```env
   SPECIFIC_EXPERTS=Andrew Erickson (FantasyPros),Pat Fitzmaurice (FantasyPros),Dave Richard (CBS Sports)
   ```

2. **Run in headless mode** (no browser window):
   ```env
   HEADLESS=true
   ```

3. **Save screenshots** for debugging:
   ```env
   SAVE_SCREENSHOTS=true
   ```

### Convenience Commands

**Makefile Commands:**
```bash
make scrape-headless   # Run without browser window
make analyze-top20     # Show top 20 players
make analyze-top50     # Show top 50 players
make clean             # Clean output files
make shell             # Python shell with imports
make check-env         # Check environment setup
make debug             # Run with debug logging
```

**Python Manager Commands:**
```bash
python manage.py scrape-headless    # Run without browser
python manage.py player "Name"      # Look up specific player
python manage.py analyze-export     # Export consensus list
python manage.py clean              # Clean output files
python manage.py shell              # Interactive Python shell
```

## Output

The scraper generates multiple output files in the `output/` directory:

1. **expert_rankings_TIMESTAMP.csv**: 
   - Main output with all expert rankings
   - Includes average rank, standard deviation, and expert count
   - Sorted by average rank

2. **expert_rankings_TIMESTAMP.xlsx**:
   - Excel file with formatting
   - Includes summary sheet with metadata

3. **deduced_rankings_TIMESTAMP.json**:
   - Raw deduced rankings data
   - Player IDs as keys

4. **player_map_TIMESTAMP.json**:
   - Mapping of player IDs to names

5. **screenshots/** (if enabled):
   - Screenshots of each expert pair selection

## Example Output

```csv
Player ID,Player,Andrew Erickson (FantasyPros),Pat Fitzmaurice (FantasyPros),...,Average Rank,Std Dev,Expert Count
12345,Christian McCaffrey,1.0,1.0,...,1.2,0.4,25
23456,Austin Ekeler,2.0,3.0,...,2.5,0.7,25
...
```

## Troubleshooting

### Common Issues

1. **Login fails**:
   - Verify credentials in `.env` file (must be valid FantasyPros account)
   - Ensure you can log in manually at [fantasypros.com/accounts/signin/](https://www.fantasypros.com/accounts/signin/)
   - Try running with `HEADLESS=false` to see login process
   - If CAPTCHA appears, solve it manually (scraper will wait 30 seconds)
   - Check for error messages in the console output

2. **Expert not found**:
   - Expert names must match exactly (including site name in parentheses)
   - Run once without `SPECIFIC_EXPERTS` to see all available experts

3. **Timeout errors**:
   - Increase `TIMEOUT` value in `.env`
   - Check internet connection
   - Try running with fewer experts

4. **Missing rankings**:
   - Some experts may not have rankings for all players
   - Check the "Expert Count" column in output

### Debug Mode

For detailed debugging information:
```python
# In scraper.py, change:
logger.setLevel('DEBUG')
```

## Algorithm Details

The deduction algorithm works because:
- `avg(A,B) = (rank_A + rank_B) / 2`
- `avg(A,C) = (rank_A + rank_C) / 2`
- `avg(B,C) = (rank_B + rank_C) / 2`

Solving this system of equations gives us the individual rankings.

## Rate Limiting

The scraper includes built-in delays to be respectful to FantasyPros servers:
- Default 2-second delay between expert pair selections
- Configurable via `DELAY_BETWEEN_REQUESTS`

## Legal Disclaimer

This tool is for educational purposes only. Users are responsible for:
- Complying with FantasyPros Terms of Service
- Using the tool responsibly and ethically
- Not overloading servers with excessive requests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the strategic pairing approach for overcoming selection limitations
- Built with Playwright for reliable browser automation
- Uses pandas for efficient data manipulation 