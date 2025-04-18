import os
import logging
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from scrapers.nike_scraper import NikeScraper
from scrapers.adidas_scraper import AdidasScraper
from supabase_client import SupabaseClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Create directories if they don't exist
os.makedirs('screenshots', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Product mapping
PRODUCT_MAPPING = {
    'air_force_1': 'Nike Air Force 1',
    'argentina_jersey': 'Camiseta Aniversario Argentina'
}

# Product ID mapping for saving to JSON/Supabase
PRODUCT_ID_MAPPING = {
    'air_force_1': 'nike-air-force-1',
    'argentina_jersey': 'camiseta-aniversario-argentina'
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

def save_results(results: List[Dict[str, Any]], save_to_supabase: bool = True):
    """Save scraping results to a JSON file and optionally to Supabase"""
    logger.info("Processing scraping results")
    
    # Process each result
    processed_results = []
    for result in results:
        product_key = result.get('product_key')
        product_name = PRODUCT_MAPPING.get(product_key, product_key)
        
        # Get product_id from mapping or generate from product name
        product_id = PRODUCT_ID_MAPPING.get(product_key, product_name.lower().replace(' ', '-'))
        
        # Create the base structure
        processed_result = {
            'product_id': product_id,
            'created_at': datetime.now().isoformat(),
            'data': {},
            'uuid': str(uuid.uuid4())
        }
        
        # Initialize the data structure
        data = {}
        
        # Process Argentina price
        
        # Process Argentina price (remove thousands separator if present)
        ar_price_raw = result.get('ar_price')
        ar_price = None

        if ar_price_raw is not None:
            # Forzar a string, limpiar puntos, convertir a float
            ar_price_str = str(ar_price_raw).replace('.', '').replace(',', '.')
            try:
                ar_price = float(ar_price_str)
            except ValueError:
                logger.warning(f"Precio AR inválido para {product_key}: {ar_price_raw}")

        ar_url = result.get('ar_url')
        if ar_price:
            data['AR'] = {
                'value': ar_price,
                'source': ar_url,
                'currency': 'ARS',
                'description': f"Obtenido de {ar_url}"
            }
        elif ar_url:
            logger.error(f"No se pudo extraer el precio para {product_name} del sitio de Argentina: {ar_url}")
        
        # Process US price
        us_price = result.get('us_price')
        us_url = result.get('us_url')
        if us_price:
            data['US'] = {
                'value': us_price,
                'source': us_url,
                'currency': 'USD',
                'description': f"Obtenido de {us_url}"
            }
        elif us_url:
            logger.error(f"No se pudo extraer el precio para {product_name} del sitio de Estados Unidos: {us_url}")
        
        # Add exchange rates from API
        try:
            import requests
            
            # Get the dollar rates from the API
            response = requests.get('https://dolarapi.com/v1/dolares')
            if response.status_code == 200:
                dollar_data = response.json()
                data['exchange_rates'] = dollar_data
                
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
                    
                    logger.info(f"{product_name} precio AR en USD blue: ${ar_in_usd_blue:.2f}")
                    logger.info(f"{product_name} precio AR en USD oficial: ${ar_in_usd_oficial:.2f}")
            else:
                logger.error(f"Failed to fetch dollar rates: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching dollar rates: {e}")
        
        # Add the data to the result
        processed_result['data'] = data
        
        # Add a detailed description with screenshots in Spanish
        details = f"Datos de precio para {product_name} obtenidos el {datetime.now().strftime('%Y-%m-%d')}\n\n---\n\n"
        
        # Determine which scraper was used based on product_key
        scraper_prefix = 'nike' if product_key == 'air_force_1' else 'adidas'
        
        # Get the most recent screenshots
        screenshots = {}
        for filename in os.listdir('screenshots'):
            if not filename.endswith('.png'):
                continue
                
            if scraper_prefix in filename.lower():
                if 'ar_' in filename.lower():
                    if 'ar' not in screenshots or filename > screenshots['ar']:
                        screenshots['ar'] = filename
                elif 'us_' in filename.lower():
                    if 'us' not in screenshots or filename > screenshots['us']:
                        screenshots['us'] = filename
        
        # Add Argentina screenshot if available
        if 'AR' in data and 'ar' in screenshots:
            ar_screenshot_path = f"screenshots/{screenshots['ar']}"
            details += f"🇦🇷 **Argentina**  \n\n![{product_name} Argentina]({ar_screenshot_path})\n\n---\n\n"
        
        # Add US screenshot if available
        if 'US' in data and 'us' in screenshots:
            us_screenshot_path = f"screenshots/{screenshots['us']}"
            details += f"🇺🇸 **Estados Unidos**  \n\n![{product_name} Estados Unidos]({us_screenshot_path})"
        
        processed_result['details'] = details
        
        processed_results.append(processed_result)
    
    # Save to file
    filename = f"data/scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(processed_results, f, indent=2)
    
    logger.info(f"Results saved to {filename}")
    
    # Save to Supabase if requested
    if save_to_supabase:
        try:
            # Initialize Supabase client
            supabase = SupabaseClient()
            
            # Save all results to Supabase at once
            for result in processed_results:
                supabase.save_price_data(result)
        except Exception as e:
            logger.error(f"Error saving to Supabase: {e}")
    
    return filename

async def main():
    """Main function to run scrapers and save results"""
    logger.info("Starting price scraper")
    
    # Load environment variables
    load_dotenv()
    
    # Check if debug mode is enabled
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Check if we should save to Supabase
    save_to_supabase = os.getenv('SAVE_TO_SUPABASE', 'true').lower() == 'true'
    
    try:
        # Run scrapers concurrently
        results = await asyncio.gather(
            run_nike_scraper(debug),
            run_adidas_scraper(debug)
        )
        
        # Filter results to keep only those with complete data
        successful_results = []
        for result in results:
            product_key = result.get('product_key')
            if not product_key:
                continue
                
            product_name = PRODUCT_MAPPING.get(product_key, product_key)
            
            # Check if we have both AR and US prices
            if result.get('ar_price') is None or result.get('us_price') is None:
                logger.error(f"Incomplete data for {product_name}: AR price: {result.get('ar_price')}, US price: {result.get('us_price')}")
                logger.warning(f"Skipping {product_name} due to incomplete data")
            else:
                logger.info(f"Complete data for {product_name}: AR price: {result.get('ar_price')}, US price: {result.get('us_price')}")
                successful_results.append(result)
        
        if successful_results:
            # Save successful results to file and optionally to Supabase
            save_results(successful_results, save_to_supabase=save_to_supabase)
            logger.info(f"Price scraping completed with {len(successful_results)} of {len(results)} products successfully scraped")
        else:
            logger.error("Price scraping completed with errors. No data saved.")
    except Exception as e:
        logger.error(f"Error running scrapers: {e}")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
