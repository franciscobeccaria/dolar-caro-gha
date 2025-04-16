import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from scrapers.nike_scraper import NikeScraper
from scrapers.adidas_scraper import AdidasScraper
from supabase_client import SupabaseClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Create screenshots directory if it doesn't exist
os.makedirs('screenshots', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Product mapping for database
PRODUCT_MAPPING = {
    'air_force_1': 'Nike Air Force 1',
    'argentina_jersey': 'Argentina Anniversary Jersey'
}

# Currency mapping
CURRENCY_MAPPING = {
    'AR': 'ARS',
    'US': 'USD',
    'BR': 'BRL',
    'CL': 'CLP'
}

async def run_nike_scraper(debug: bool = False) -> Dict[str, Any]:
    """Run the Nike scraper"""
    logger.info("Starting Nike scraper")
    try:
        scraper = NikeScraper(debug=debug)
        return await scraper.scrape(product_key='air_force_1')
    except Exception as e:
        logger.error(f"Nike scraper error: {e}")
        return {"product_key": "air_force_1"}

async def run_adidas_scraper(debug: bool = False) -> Dict[str, Any]:
    """Run the Adidas scraper"""
    logger.info("Starting Adidas scraper")
    try:
        scraper = AdidasScraper(debug=debug)
        return await scraper.scrape(product_key='argentina_jersey')
    except Exception as e:
        logger.error(f"Adidas scraper error: {e}")
        return {"product_key": "argentina_jersey"}

def save_to_supabase(results: List[Dict[str, Any]]):
    """Save scraping results to Supabase"""
    logger.info("Saving results to Supabase")
    
    # Initialize Supabase client
    try:
        supabase = SupabaseClient()
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return
    
    # Fetch all dollar rates from the API
    logger.info("Fetching all dollar rates from API")
    all_rates = supabase.fetch_all_dollar_rates()
    
    # Get specific rates we need
    blue_rate = None
    oficial_rate = None
    for rate_data in all_rates:
        if rate_data.get('casa') == 'blue':
            blue_rate = rate_data.get('venta')
        elif rate_data.get('casa') == 'oficial':
            oficial_rate = rate_data.get('venta')
    
    # If API failed, try to get rates from database
    if not blue_rate:
        blue_rate = supabase.get_blue_dollar_rate()
    
    logger.info(f"Current blue dollar rate: {blue_rate}")
    logger.info(f"Current oficial dollar rate: {oficial_rate}")
    
    # Process each result
    for result in results:
        product_key = result.get('product_key')
        product_name = PRODUCT_MAPPING.get(product_key, product_key)
        
        # Process Argentina price
        ar_price = result.get('ar_price')
        ar_url = result.get('ar_url')
        if ar_price:
            # Calculate USD values if rates are available
            value_usd_blue = None
            
            if blue_rate:
                value_usd_blue = ar_price / blue_rate
                logger.info(f"{product_name} AR price in USD blue: ${value_usd_blue:.2f}")
                
            if oficial_rate:
                value_usd_oficial = ar_price / oficial_rate
                logger.info(f"{product_name} AR price in USD oficial: ${value_usd_oficial:.2f}")
            
            # Insert Argentina price
            supabase.insert_price(
                product_name=product_name,
                country_code='AR',
                value=ar_price,
                currency='ARS',
                value_usd_blue=value_usd_blue,
                source_type='scraping',
                description=f"Scraped from {ar_url}"
            )
        elif ar_url:
            logger.error(f"Failed to extract price for {product_name} from Argentina site: {ar_url}")
        
        # Process US price
        us_price = result.get('us_price')
        us_url = result.get('us_url')
        if us_price:
            # Insert US price
            supabase.insert_price(
                product_name=product_name,
                country_code='US',
                value=us_price,
                currency='USD',
                source_type='scraping',
                description=f"Scraped from {us_url}"
            )
        elif us_url:
            logger.error(f"Failed to extract price for {product_name} from US site: {us_url}")
            
            # Calculate and log price comparison if both prices and rates are available
            if ar_price and blue_rate:
                ar_in_usd_blue = ar_price / blue_rate
                price_ratio_blue = (us_price / ar_in_usd_blue) * 100
                logger.info(f"{product_name} price comparison: US is {price_ratio_blue:.2f}% of AR price (blue dollar)")
                
            if ar_price and oficial_rate:
                ar_in_usd_oficial = ar_price / oficial_rate
                price_ratio_oficial = (us_price / ar_in_usd_oficial) * 100
                logger.info(f"{product_name} price comparison: US is {price_ratio_oficial:.2f}% of AR price (oficial dollar)")

async def main():
    """Main function to run scrapers and save results"""
    logger.info("Starting price scraper")
    
    # Load environment variables
    load_dotenv()
    
    # Check if debug mode is enabled
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    try:
        # Run scrapers concurrently
        results = await asyncio.gather(
            run_nike_scraper(debug),
            run_adidas_scraper(debug)
        )
        
        # Save results to Supabase
        save_to_supabase(results)
        
        logger.info("Price scraping completed successfully")
    except Exception as e:
        logger.error(f"Error running scrapers: {e}")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
