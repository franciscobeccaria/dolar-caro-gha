import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('supabase_client')

class SupabaseClient:
    """Client for interacting with Supabase"""
    
    def __init__(self):
        """Initialize the Supabase client"""
        # Load environment variables
        load_dotenv()
        
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the .env file")
        
        # Initialize Supabase client
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
        
        # Ensure reference data exists
        self.ensure_reference_data_exists()
    
    def insert_price(self, 
                     product_name: str, 
                     country_code: str, 
                     value: float, 
                     currency: str, 
                     value_usd_blue: Optional[float] = None, 
                     source_type: str = 'scraping', 
                     description: Optional[str] = None,
                     image_url: Optional[str] = None) -> Dict[str, Any]:
        """Insert a price record into the prices table
        
        Args:
            product_name: Name of the product (e.g., 'Nike Air Force 1', 'Argentina Anniversary Jersey')
            country_code: Country ISO code (e.g., 'AR', 'US')
            value: The price value in the local currency
            currency: Currency code (e.g., 'ARS', 'USD')
            value_usd_blue: Optional value in USD using blue dollar rate (for Argentina)
            source_type: Type of source for the price data
            description: Optional description or additional information
            image_url: Optional URL to an image of the product
        
        Returns:
            The inserted record or None if failed
        """
        try:
            # Get product_id from products table
            product_result = self.client.table('products')\
                .select('id')\
                .ilike('name', f'%{product_name}%')\
                .execute()
            
            if not product_result.data:
                logger.error(f"Product not found: {product_name}")
                return None
            
            product_id = product_result.data[0]['id']
            
            # Get country_id from countries table
            country_result = self.client.table('countries')\
                .select('id')\
                .eq('iso_code', country_code)\
                .execute()
            
            if not country_result.data:
                logger.error(f"Country not found: {country_code}")
                return None
            
            country_id = country_result.data[0]['id']
            
            # Get source_id from sources table
            source_result = self.client.table('sources')\
                .select('id')\
                .eq('type', source_type)\
                .execute()
            
            if not source_result.data:
                logger.error(f"Source not found: {source_type}")
                return None
            
            source_id = source_result.data[0]['id']
            
            # Prepare the data
            now = datetime.now().strftime('%Y-%m-%d')
            data = {
                "product_id": product_id,
                "country_id": country_id,
                "source_id": source_id,
                "value": value,
                "currency": currency,
                "date": now,
                "description": description
            }
            
            # Add optional fields if provided
            if value_usd_blue is not None:
                data["value_usd_blue"] = value_usd_blue
            
            if image_url is not None:
                data["image_url"] = image_url
            
            logger.info(f"Inserting price record: {data}")
            
            # Use RPC call to bypass RLS policy
            # The RPC method is working correctly, so we'll only use that
            # Use direct insert with the Supabase client
            try:
                result = self.client.table('prices').insert(data).execute()
                if result.data and len(result.data) > 0:
                    logger.info(f"Successfully inserted price record with ID: {result.data[0].get('id')}")
                    return result.data[0]
                else:
                    logger.info("Successfully inserted price record (no ID returned)")
                    return {'success': True}
            except Exception as e:
                # If direct insert fails, try with RPC function
                try:
                    result = self.client.rpc(
                        'insert_price_record',
                        {
                            'p_product_id': product_id,
                            'p_country_id': country_id,
                            'p_source_id': source_id,
                            'p_value': value,
                            'p_currency': currency,
                            'p_date': now,
                            'p_description': description,
                            'p_value_usd_blue': value_usd_blue,
                            'p_image_url': image_url
                        }
                    ).execute()
                    
                    # The RPC function returns {'id': number, 'success': true}
                    logger.info(f"Successfully inserted price record via RPC: {result.data}")
                    return result.data[0] if isinstance(result.data, list) and result.data else result.data or {'success': True}
                except Exception as rpc_error:
                    # Check if the error message actually contains a successful response
                    error_str = str(rpc_error)
                    if "'id'" in error_str and "'success'" in error_str:
                        logger.info(f"Successfully inserted price record despite error format: {error_str}")
                        return {'success': True}
                    else:
                        logger.error(f"Failed to insert price record: {rpc_error}")
                        return None
        except Exception as e:
            logger.error(f"Error inserting price record: {e}")
            return None
            
    def ensure_reference_data_exists(self):
        """Ensure that reference data (products, countries, sources) exists in the database
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if products exist
            products_result = self.client.table('products').select('count(*)', count='exact').limit(1).execute()
            if products_result.count == 0:
                # Insert Nike Air Force 1
                self.client.table('products').insert({
                    "name": "Nike Air Force 1",
                    "description": "Classic white sneakers",
                    "brand": "Nike",
                    "category": "Shoes"
                }).execute()
                
                # Insert Argentina Jersey
                self.client.table('products').insert({
                    "name": "Argentina Anniversary Jersey",
                    "description": "50th Anniversary Argentina National Team Jersey",
                    "brand": "Adidas",
                    "category": "Sports Apparel"
                }).execute()
                
                logger.info("Added product reference data")
            
            # Check if countries exist
            countries_result = self.client.table('countries').select('count(*)', count='exact').limit(1).execute()
            if countries_result.count == 0:
                # Insert Argentina
                self.client.table('countries').insert({
                    "name": "Argentina",
                    "iso_code": "AR",
                    "currency": "ARS"
                }).execute()
                
                # Insert United States
                self.client.table('countries').insert({
                    "name": "United States",
                    "iso_code": "US",
                    "currency": "USD"
                }).execute()
                
                logger.info("Added country reference data")
            
            # Check if sources exist
            sources_result = self.client.table('sources').select('count(*)', count='exact').limit(1).execute()
            if sources_result.count == 0:
                # Insert scraping source
                self.client.table('sources').insert({
                    "type": "scraping",
                    "description": "Automated web scraping using Playwright",
                    "method": "playwright"
                }).execute()
                
                logger.info("Added source reference data")
                
            # Update blue dollar rate in Argentina country record
            blue_rate = self.get_blue_dollar_rate()
            if blue_rate:
                self.client.table('countries')\
                    .update({"blue_usd_rate": blue_rate})\
                    .eq('iso_code', 'AR')\
                    .execute()
                logger.info(f"Updated Argentina blue dollar rate to {blue_rate}")
            
            return True
        except Exception as e:
            logger.error(f"Error ensuring reference data exists: {e}")
            return False
    
    def get_latest_prices(self, product_id: Optional[str] = None, country_id: Optional[str] = None, limit: int = 10) -> list:
        """Get the latest price records
        
        Args:
            product_id: Optional filter by product ID
            country_id: Optional filter by country ID
            limit: Maximum number of records to return
        
        Returns:
            List of price records
        """
        query = self.client.table('prices').select('*').order('date', desc=True).limit(limit)
        
        # Apply filters if provided
        if product_id:
            query = query.eq('product_id', product_id)
        
        if country_id:
            query = query.eq('country_id', country_id)
        
        try:
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching latest prices: {e}")
            return []
    
    def get_blue_dollar_rate(self) -> Optional[float]:
        """Get the latest blue dollar rate from dolarapi.com
        
        Returns:
            The blue dollar rate (venta/selling price) or None if not found
        """
        try:
            # First try to get from the database
            try:
                result = self.client.table('exchange_rates')\
                    .select('rate')\
                    .eq('source', 'blue')\
                    .eq('from_currency', 'USD')\
                    .eq('to_currency', 'ARS')\
                    .order('date', desc=True)\
                    .limit(1)\
                    .execute()
                
                if result.data and len(result.data) > 0:
                    rate = result.data[0]['rate']
                    logger.info(f"Found blue dollar rate in database: {rate}")
                    return rate
            except Exception as db_error:
                logger.warning(f"Error getting blue dollar rate from database: {db_error}")
            
            # If not found in database, fetch from API
            return self.fetch_dollar_rate('blue')
        except Exception as e:
            logger.error(f"Error getting blue dollar rate: {e}")
            return None
            
    def fetch_dollar_rate(self, rate_type: str = 'blue') -> Optional[float]:
        """Fetch the latest dollar rate from dolarapi.com
        
        Args:
            rate_type: Type of dollar rate to fetch ('blue', 'oficial', 'bolsa', etc.)
            
        Returns:
            The dollar rate (venta/selling price) or None if not found
        """
        try:
            response = requests.get('https://dolarapi.com/v1/dolares')
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            data = response.json()
            logger.info(f"Successfully fetched dollar rates from API: {len(data)} rates available")
            
            # Find the requested rate type
            for rate_data in data:
                if rate_data.get('casa') == rate_type:
                    rate = rate_data.get('venta')  # Use selling price
                    logger.info(f"Found {rate_type} dollar rate: {rate}")
                    return rate
            
            logger.warning(f"Rate type '{rate_type}' not found in API response")
            return None
        except Exception as e:
            logger.error(f"Error fetching dollar rate from API: {e}")
            return None
    
    def fetch_all_dollar_rates(self) -> List[Dict[str, Any]]:
        """Fetch all dollar rates from dolarapi.com
        
        Returns:
            List of all dollar rates or empty list if failed
        """
        try:
            response = requests.get('https://dolarapi.com/v1/dolares')
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            data = response.json()
            logger.info(f"Successfully fetched all dollar rates from API: {len(data)} rates available")
            
            # Store all rates in the database
            for rate_data in data:
                rate_type = rate_data.get('casa')
                rate = rate_data.get('venta')  # Use selling price
                if rate_type and rate:
                    self.store_exchange_rate('USD', 'ARS', rate, rate_type)
            
            return data
        except Exception as e:
            logger.error(f"Error fetching all dollar rates from API: {e}")
            return []
    
    def store_exchange_rate(self, from_currency: str, to_currency: str, rate: float, source: str) -> Dict[str, Any]:
        """Store an exchange rate in the database
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'ARS')
            rate: Exchange rate value
            source: Source of the rate (e.g., 'blue', 'oficial')
            
        Returns:
            The inserted record or None if failed
        """
        try:
            # Prepare the data
            now = datetime.now().isoformat()
            data = {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "source": source,
                "date": now
            }
            
            logger.info(f"Storing exchange rate: {from_currency}/{to_currency} = {rate} ({source})")
            
            # Insert the data
            result = self.client.table('exchange_rates').insert(data).execute()
            
            # If this is a blue dollar rate, update the countries table
            if source == 'blue' and from_currency == 'USD' and to_currency == 'ARS':
                try:
                    self.client.table('countries')\
                        .update({"blue_usd_rate": rate})\
                        .eq('iso_code', 'AR')\
                        .execute()
                    logger.info(f"Updated Argentina blue dollar rate to {rate}")
                except Exception as update_error:
                    logger.error(f"Error updating country blue dollar rate: {update_error}")
            
            logger.info(f"Successfully stored exchange rate with ID: {result.data[0]['id']}")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error storing exchange rate: {e}")
            return None
