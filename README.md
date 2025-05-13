# Investor Profile Scraper

A Python-based web scraper that extracts investor profile data from Signal.nfx and saves it to CSV files.

## Features
- Scrapes investor profiles including:
  - Basic information (name, current company)
  - Investment preferences (range, sweet spot, fund size)
  - Experience history
  - Sector rankings
  - Social links
  - Network memberships
  - Education background
  - Previous investments
  - Profile images
- Supports parallel scraping with configurable worker count
- Maintains progress tracking with `progress.csv`
- Handles authentication and session management
- Robust error handling and logging

## Requirements
- Python 3.8+
- Required packages (see `requirements.txt`):
  - selenium
  - beautifulsoup4
  - pandas
  - lxml

## Installation
1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt