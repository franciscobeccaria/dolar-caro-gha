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
        
        # Explicitly try to use the service role key first, then fall back to regular key
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE')
        regular_key = os.getenv('SUPABASE_KEY')
        
        # Determine which key to use, prioritizing service role key
        supabase_key = service_role_key if service_role_key else regular_key
        
        # Log which key is being used (without exposing the actual key)
        if service_role_key:
            logger.info("Using SUPABASE_SERVICE_ROLE key for authentication")
        elif regular_key:
            logger.warning("Using regular SUPABASE_KEY - this may not bypass RLS policies")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and either SUPABASE_SERVICE_ROLE or SUPABASE_KEY must be set in environment variables")
        
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
            
            # Check for RLS policy violations
            rls_error = False
            error_details = {}
            
            # Print more detailed error information if available
            if hasattr(e, 'response'):
                try:
                    error_details = e.response.json()
                    logger.error(f"Response error details: {error_details}")
                    
                    # Check if this is an RLS policy violation
                    if isinstance(error_details, dict):
                        error_message = error_details.get('message', '')
                        error_code = error_details.get('code', '')
                        
                        if 'row-level security policy' in error_message or error_code == '42501':
                            rls_error = True
                            logger.error("RLS policy violation detected. Make sure you're using the SUPABASE_SERVICE_ROLE key.")
                            logger.error("If running in GitHub Actions, check that the secret is correctly configured.")
                except Exception as parse_error:
                    logger.error(f"Could not parse error response: {e.response} - {parse_error}")
            
            # Provide specific guidance for RLS errors
            if rls_error:
                logger.error("\n=== TROUBLESHOOTING RLS ERRORS ===")
                logger.error("1. Ensure SUPABASE_SERVICE_ROLE is correctly set in environment variables")
                logger.error("2. If using GitHub Actions, check that the secret is properly configured")
                logger.error("3. Verify that the service role key has the correct permissions")
                logger.error("4. Check the RLS policies in your Supabase dashboard")
                logger.error("===============================\n")
            
            return None
