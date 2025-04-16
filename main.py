import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from scrapers.nike_scraper import NikeScraper
from scrapers.adidas_scraper import AdidasScraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Create directories if they don't exist
os.makedirs('screenshots', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Product mapping
PRODUCT_MAPPING = {
    'air_force_1': 'Nike Air Force 1',
    'argentina_jersey': 'Argentina Anniversary Jersey'
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

def save_results_to_file(results: List[Dict[str, Any]]):
    """Save scraping results to a JSON file"""
    logger.info("Saving results to file")
    
    # Process each result
    processed_results = []
    for result in results:
        product_key = result.get('product_key')
        product_name = PRODUCT_MAPPING.get(product_key, product_key)
        
        processed_result = {
            'product_name': product_name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Process Argentina price
        ar_price = result.get('ar_price')
        ar_url = result.get('ar_url')
        if ar_price:
            processed_result['ar_price'] = ar_price
            processed_result['ar_url'] = ar_url
            processed_result['ar_currency'] = 'ARS'
        elif ar_url:
            logger.error(f"Failed to extract price for {product_name} from Argentina site: {ar_url}")
        
        # Process US price
        us_price = result.get('us_price')
        us_url = result.get('us_url')
        if us_price:
            processed_result['us_price'] = us_price
            processed_result['us_url'] = us_url
            processed_result['us_currency'] = 'USD'
        elif us_url:
            logger.error(f"Failed to extract price for {product_name} from US site: {us_url}")
        
        # Add exchange rates from API
        # Fetch the dollar API data
        try:
            import requests
            
            # Get the dollar rates from the API
            response = requests.get('https://dolarapi.com/v1/dolares')
            if response.status_code == 200:
                dollar_data = response.json()
                processed_result['exchange_rates'] = dollar_data
                
                # Create a dictionary for easier access to rates by type
                rates_by_type = {}
                for rate in dollar_data:
                    rates_by_type[rate.get('casa')] = rate
                
                # Log some useful information for reference
                blue_rate = rates_by_type.get('blue', {}).get('venta')
                oficial_rate = rates_by_type.get('oficial', {}).get('venta')
                
                if ar_price and us_price and blue_rate and oficial_rate:
                    ar_in_usd_blue = ar_price / blue_rate
                    ar_in_usd_oficial = ar_price / oficial_rate
                    
                    logger.info(f"{product_name} AR price in USD blue: ${ar_in_usd_blue:.2f}")
                    logger.info(f"{product_name} AR price in USD oficial: ${ar_in_usd_oficial:.2f}")
            else:
                logger.error(f"Failed to fetch dollar rates: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching dollar rates: {e}")
        
        processed_results.append(processed_result)
    
    # Save to file
    filename = f"data/scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(processed_results, f, indent=2)
    
    logger.info(f"Results saved to {filename}")
    return filename

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
        
        # Save results to file
        save_results_to_file(results)
        
        logger.info("Price scraping completed successfully")
    except Exception as e:
        logger.error(f"Error running scrapers: {e}")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
