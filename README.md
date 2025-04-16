# Price Scraper

A serverless web scraping tool that collects product prices from Nike and Adidas websites across different countries (Argentina and USA) and stores them in a structured JSON format with optional Supabase database integration for international price comparison analysis.

## Project Overview

This project aims to compare product prices across different countries to analyze purchasing power and international price differences. It currently supports scraping prices for Nike Air Force 1 sneakers and Argentina Anniversary Jersey from both US and Argentina online stores, with plans to expand to more countries (Chile, Brazil) and additional products. The project is designed to help understand purchasing power differences across countries and visualize dollar value variations.

## Features

- Automated web scraping of Nike and Adidas product pages
- Scrapes prices for Nike Air Force 1 and Argentina Anniversary Jersey
- Real-time exchange rate fetching from [dolarapi.com](https://dolarapi.com/v1/dolares)
- Comprehensive exchange rate data (official, blue, CCL, crypto, etc.)
- Supports multiple countries (currently US and Argentina)
- Price comparison calculations using various dollar rates
- Structured JSON data storage with screenshots embedded in details
- Optional Supabase database integration
- Automatic screenshot capture for visual verification
- GitHub Actions workflow for scheduled scraping

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

The project uses a Supabase database with a single `precios` table that stores all price data in a structured JSON format. The schema is provided in the `supabase_schema.sql` file.

### Supabase Setup

Create a `precios` table in your Supabase project with the following schema:

```sql
CREATE TABLE IF NOT EXISTS public.precios (
  id BIGSERIAL PRIMARY KEY,
  product_id TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  data JSONB NOT NULL,
  uuid UUID NOT NULL,
  details TEXT,
  CONSTRAINT unique_product_id_created_at UNIQUE (product_id, created_at)
);
```

The `data` JSONB field contains a structured object with:

- Country-specific price information (AR, US)
- Exchange rates from various sources (official, blue, etc.)

The `details` field contains a markdown-formatted description with embedded screenshots of the product pages.

#### Row Level Security (RLS)

Make sure to set up appropriate Row Level Security (RLS) policies to allow your application to insert data. The following policy is required:

```sql
CREATE POLICY "Allow inserts for authenticated users"
  ON public.precios FOR INSERT
  TO authenticated
  USING (true);
```

Without this policy, you'll encounter the error: `new row violates row-level security policy for table "precios"`.

A complete set of RLS policies is provided in the `supabase_schema.sql` file.

## Usage

Run the scraper manually:

```bash
python main.py
```

Or with Supabase integration disabled:

```bash
SAVE_TO_SUPABASE=false python main.py
```

The scraper will:

1. Scrape prices from Nike and Adidas websites for both US and Argentina
2. Capture screenshots of each product page for reference
3. Fetch the latest exchange rates from dolarapi.com (including official, blue, CCL, etc.)
4. Save the data locally in a structured JSON format in the `data/` directory
5. Store the complete data in the Supabase `precios` table (if SAVE_TO_SUPABASE=true)

The saved data includes:

- Product details and prices from each country
- Screenshots embedded in the details field
- Comprehensive exchange rate information
- Calculated USD equivalents using different exchange rates

### Data Structure

The JSON data is structured as follows:

```json
{
  "product_id": "nike-air-force-1",
  "created_at": "2025-04-16T18:43:22.842088",
  "data": {
    "AR": {
      "value": 199.999,
      "source": "https://www.nike.com.ar/nike-air-force-1--07-cw2288-111/p",
      "currency": "ARS",
      "description": "Scraped from Nike Argentina"
    },
    "US": {
      "value": 115.0,
      "source": "https://www.nike.com/t/air-force-1-07-mens-shoes-5QFp5Z/CW2288-111",
      "currency": "USD",
      "description": "Scraped from Nike US"
    },
    "exchange_rates": [
      {
        "moneda": "USD",
        "casa": "oficial",
        "nombre": "Oficial",
        "compra": 1110,
        "venta": 1160,
        "fechaActualizacion": "2025-04-16T16:41:00.000Z"
      }
      // Additional exchange rates...
    ]
  },
  "uuid": "79b0326f-dda8-4af8-b71f-fb8076af0ba2",
  "details": "Price data with embedded screenshots..."
}
```

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
├── data/               # Directory for saved JSON data
├── screenshots/        # Directory for product page screenshots
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
