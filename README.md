# Price Scraper

A serverless web scraping tool that collects product prices from Nike and Adidas websites across different countries (Argentina and USA) and stores them in a Supabase database for international price comparison analysis.

## Project Overview

This project aims to compare product prices across different countries to analyze purchasing power and international price differences. It currently supports scraping prices for Nike Air Force 1 sneakers and Argentina Anniversary Jersey from both US and Argentina online stores, with plans to expand to more countries (Chile, Brazil) and additional products.

## Features

- Automated web scraping of Nike and Adidas product pages
- Scrapes prices for Nike Air Force 1 and Argentina Anniversary Jersey
- Real-time exchange rate fetching from [dolarapi.com](https://dolarapi.com/v1/dolares)
- Supports multiple countries (currently US and Argentina)
- Price comparison calculations using both official and blue dollar rates
- Data storage in Supabase database
- Screenshot capture for debugging and verification

## Project Structure

### Core Files

- `main.py` - Main script that orchestrates the scraping process and data storage
- `supabase_client.py` - Client for interacting with the Supabase database
- `scrapers/` - Directory containing scraper implementations:
  - `base_scraper.py` - Base class with common scraping functionality
  - `nike_scraper.py` - Nike-specific scraper implementation
  - `adidas_scraper.py` - Adidas-specific scraper implementation

### Configuration

- `.env` - Environment variables for Supabase credentials
- `requirements.txt` - Python dependencies

### Output Directories

- `screenshots/` - Contains screenshots captured during scraping
- `data/` - Directory for any temporary data storage

## Setup and Usage

### Prerequisites

- Python 3.8+
- Playwright
- Supabase account and project

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```
4. Create a `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

### Database Setup

Ensure your Supabase database has the following tables:

1. `products` - Product information
2. `countries` - Country information
3. `sources` - Data source information
4. `prices` - Price records with foreign keys to the above tables
5. `exchange_rates` - Currency exchange rate records

Also, make sure to set up the `insert_price_record` RPC function and appropriate Row Level Security (RLS) policies.

### Supabase Setup

Create a `prices` table in your Supabase project with the following schema:

```sql
create table prices (
  id uuid default uuid_generate_v4() primary key,
  product_id text not null,
  country_id text not null,
  value float not null,
  currency text not null,
  value_usd_blue float,
  source_id text not null,
  date timestamp with time zone default now(),
  description text
);
```

Optionally, create an `exchange_rates` table to store blue dollar rates:

```sql
create table exchange_rates (
  id uuid default uuid_generate_v4() primary key,
  from_currency text not null,
  to_currency text not null,
  rate float not null,
  source text not null,
  date timestamp with time zone default now()
);
```

## Usage

Run the scraper manually:

```bash
python main.py
```

The scraper will:
1. Scrape prices from Nike and Adidas websites for both US and Argentina
2. Retrieve the latest blue dollar rate from Supabase (if available)
3. Calculate USD blue equivalents for Argentine prices
4. Store all results in the Supabase `prices` table

## GitHub Actions

The project includes a GitHub Actions workflow that runs the scraper daily. To use it:

1. Push the code to a GitHub repository
2. Add your Supabase credentials as repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

## Project Structure

```
├── .github/workflows/  # GitHub Actions workflows
│   └── scraper.yml     # Daily scraper workflow
├── scrapers/           # Scraper modules
│   ├── __init__.py
│   ├── base_scraper.py # Base scraper class
│   ├── nike_scraper.py # Nike-specific scraper
│   └── adidas_scraper.py # Adidas-specific scraper
├── .env.example        # Environment variables template
├── main.py             # Main entry point
├── requirements.txt    # Python dependencies
├── supabase_client.py  # Supabase client wrapper
└── README.md           # This file
```

## Extending the Project

To add more products or websites:

1. Create a new scraper class that extends `BaseScraper`
2. Add product URLs and fallback prices
3. Implement the scraping logic
4. Update the `PRODUCT_MAPPING` in `main.py`
5. Add the new scraper to the `main()` function

## License

MIT
