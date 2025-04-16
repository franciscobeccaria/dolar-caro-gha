from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime
import asyncio
from playwright.async_api import async_playwright
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, debug: bool = False, screenshots_dir: str = None):
        """Initialize the scraper"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.debug = debug
        
        # Setup screenshots directory if debugging is enabled
        if debug and screenshots_dir is None:
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'screenshots')
        
        self.screenshots_dir = screenshots_dir
        if self.screenshots_dir:
            os.makedirs(self.screenshots_dir, exist_ok=True)
    
    @abstractmethod
    async def scrape(self) -> Dict[str, Any]:
        """Main scraping method to be implemented by subclasses"""
        pass
    
    async def take_screenshot(self, page, name: str) -> str:
        """Take a screenshot if debugging is enabled"""
        if not self.debug or not self.screenshots_dir:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        await page.screenshot(path=filepath)
        self.logger.info(f"Screenshot saved to {filepath}")
        return filepath
    
    async def create_browser_context(self, playwright, country_code: str, user_agent: str = None) -> Tuple:
        """Create a browser context with appropriate settings for the given country"""
        browser = await playwright.chromium.launch(headless=True)
        
        # Default user agent if none provided
        if user_agent is None:
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        
        # Create context with appropriate locale and user agent
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1280, 'height': 800},
            locale=self._get_locale_for_country(country_code)
        )
        
        # Create page
        page = await context.new_page()
        
        # Set extra headers based on country
        await page.set_extra_http_headers(self._get_headers_for_country(country_code))
        
        return browser, context, page
    
    def _get_locale_for_country(self, country_code: str) -> str:
        """Get the appropriate locale string for a country code"""
        locale_map = {
            'US': 'en-US',
            'AR': 'es-AR',
            'BR': 'pt-BR',
            'CL': 'es-CL'
        }
        return locale_map.get(country_code, 'en-US')
    
    def _get_headers_for_country(self, country_code: str) -> Dict[str, str]:
        """Get appropriate HTTP headers for a country code"""
        headers = {
            'Accept-Language': self._get_accept_language(country_code),
            'Sec-Ch-Ua': '"Chromium";v="122", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"'
        }
        return headers
    
    def _get_accept_language(self, country_code: str) -> str:
        """Get the appropriate Accept-Language header value for a country code"""
        language_map = {
            'US': 'en-US,en;q=0.9',
            'AR': 'es-AR,es;q=0.9',
            'BR': 'pt-BR,pt;q=0.9',
            'CL': 'es-CL,es;q=0.9'
        }
        return language_map.get(country_code, 'en-US,en;q=0.9')
    
    async def extract_price_with_selectors(self, page, selectors: List[str]) -> Optional[float]:
        """Try to extract price using multiple selectors"""
        for selector in selectors:
            try:
                # Wait for the selector with a short timeout
                await page.wait_for_selector(selector, timeout=5000)
                price_element = await page.query_selector(selector)
                
                if price_element:
                    price_text = await price_element.inner_text()
                    self.logger.info(f"Found price text with selector {selector}: {price_text}")
                    
                    # Extract the price using the appropriate method
                    price = self._extract_price_from_text(price_text)
                    if price is not None:
                        self.logger.info(f"Successfully extracted price: {price}")
                        return price
            except Exception as e:
                self.logger.warning(f"Selector {selector} failed: {e}")
        
        return None
    
    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Extract a price value from text"""
        import re
        
        # Try different patterns
        patterns = [
            r'\$\s*(\d+(?:[.,]\d+)*)',  # $199.999 or $199,999
            r'(\d+(?:[.,]\d+)*)\s*\$',  # 199.999$ or 199,999$
            r'(\d+(?:[.,]\d+)*)'         # Just numbers
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, text)
            if matches:
                # Clean up the price string
                price_str = matches.group(1).strip()
                
                # Handle different number formats
                if ',' in price_str and '.' in price_str:
                    # Format like 1,234.56
                    if price_str.find(',') < price_str.find('.'):
                        price_str = price_str.replace(',', '')
                    # Format like 1.234,56
                    else:
                        price_str = price_str.replace('.', '').replace(',', '.')
                elif ',' in price_str:
                    # Could be either 1,234 or 1,23
                    if len(price_str.split(',')[1]) > 2:
                        price_str = price_str.replace(',', '')
                    else:
                        price_str = price_str.replace(',', '.')
                
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        return None
