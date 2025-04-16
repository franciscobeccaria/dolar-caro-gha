import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from supabase import create_client

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('supabase_client')

class SupabaseClient:
    """Simple client for saving price data to Supabase"""
    
    def __init__(self):
        """Initialize the Supabase client"""
        # Load environment variables
        load_dotenv()
        
        # Get Supabase credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE') or os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY or SUPABASE_SERVICE_ROLE must be set in .env file")
        
        # Initialize Supabase client
        self.client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
    
    def save_price_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save price data to the precios table
        
        Args:
            data: The price data to save
        
        Returns:
            The saved record or None if failed
        """
        try:
            # Insert the data into the precios table
            logger.info(f"Attempting to save data for {data.get('product_id')} to Supabase")
            result = self.client.table('precios').insert(data).execute()
            
            if result.data:
                logger.info(f"Successfully saved price data for {data.get('product_id')}")
                return result.data[0]
            else:
                logger.error(f"Failed to save price data for {data.get('product_id')}")
                if hasattr(result, 'error'):
                    logger.error(f"Error details: {result.error}")
                return None
        except Exception as e:
            logger.error(f"Error saving price data: {e}")
            # Print more detailed error information if available
            if hasattr(e, 'response'):
                try:
                    error_details = e.response.json()
                    logger.error(f"Response error details: {error_details}")
                except:
                    logger.error(f"Response error (not JSON): {e.response.text if hasattr(e.response, 'text') else 'No text'}")
            return None
