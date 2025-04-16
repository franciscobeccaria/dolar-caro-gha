from .base_scraper import BaseScraper
from typing import Dict, Any, List, Optional
import asyncio
import re
from playwright.async_api import async_playwright

class NikeScraper(BaseScraper):
    """Scraper for Nike products"""
    
    def __init__(self, debug: bool = False, screenshots_dir: str = None):
        super().__init__(debug, screenshots_dir)
        self.product_urls = {
            # Air Force 1
            'air_force_1': {
                'AR': "https://www.nike.com.ar/nike-air-force-1--07-cw2288-111/p",
                'US': "https://www.nike.com/t/air-force-1-07-mens-shoes-5QFp5Z/CW2288-111"
            }
            # Add more products as needed
        }
        
        # No fallback prices - we'll use retry logic instead
    
    async def scrape(self, product_key: str = 'air_force_1') -> Dict[str, Any]:
        """Scrape prices for a Nike product"""
        if product_key not in self.product_urls:
            raise ValueError(f"Unknown product key: {product_key}")
        
        urls = self.product_urls[product_key]
        
        ar_price = None
        us_price = None
        
        async with async_playwright() as p:
            # Scrape Argentina price
            ar_price = await self._scrape_argentina(p, urls.get('AR'))
            
            # Scrape US price
            us_price = await self._scrape_us(p, urls.get('US'))
        
        return {
            "product_key": product_key,
            "ar_price": ar_price,
            "us_price": us_price,
            "ar_url": urls.get('AR'),
            "us_url": urls.get('US')
        }
    
    async def _scrape_argentina(self, playwright, url: str) -> float:
        """Scrape price from Nike Argentina with retry logic"""
        if not url:
            self.logger.error("No URL provided for Nike Argentina")
            raise ValueError("No URL provided for Nike Argentina")
        
        self.logger.info(f"Scraping Nike Argentina: {url}")
        price = None
        max_retries = 3  # Maximum number of retry attempts
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Attempt {attempt}/{max_retries} for Nike Argentina")
                
                # Create browser context for Argentina
                browser, context, page = await self.create_browser_context(playwright, 'AR')
                
                # Add cookies for Nike Argentina
                await context.add_cookies([{
                    'name': 'accept_cookies',
                    'value': 'true',
                    'domain': '.nike.com.ar',
                    'path': '/'
                }])
                
                # Use a different user agent each retry to avoid being detected as a bot
                user_agents = [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ]
                await context.add_init_script(f"navigator.userAgent='{user_agents[attempt-1]}'")
                
                # Navigate to the URL with increased timeout and more robust handling
                try:
                    # Use a longer timeout for the first attempt
                    timeout = 90000 if attempt == 1 else 120000
                    await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
                    
                    # First wait for domcontentloaded, then try to wait for networkidle with a shorter timeout
                    try:
                        await page.wait_for_load_state('networkidle', timeout=10000)
                    except Exception as load_error:
                        self.logger.warning(f"Network idle timeout, continuing anyway: {load_error}")
                    
                    # Additional wait time to ensure JavaScript loads
                    await asyncio.sleep(5)  # Increased from 3 to 5 seconds
                
                    # Take screenshot if debugging is enabled
                    screenshot_name = f"nike_ar_attempt{attempt}"
                    await self.take_screenshot(page, screenshot_name)
                    
                    # Check if we hit a Cloudflare CAPTCHA page
                    cloudflare_detected = False
                    try:
                        # Look for common Cloudflare elements
                        cloudflare_elements = [
                            '.cf-browser-verification', 'iframe[src*="cloudflare"]',
                            '.cf-error-code', '.cf-captcha-container', '#challenge-form',
                            'h1:has-text("Verifying you are human")', 'h1:has-text("Verificando que eres humano")',
                            'h1:has-text("Verifique que usted es un ser humano")'
                        ]
                        for selector in cloudflare_elements:
                            if await page.query_selector(selector):
                                cloudflare_detected = True
                                self.logger.warning(f"Cloudflare CAPTCHA detected on attempt {attempt}")
                                break
                    except Exception as cf_error:
                        self.logger.error(f"Error checking for Cloudflare: {cf_error}")
                    
                    # If Cloudflare is detected, try again with a different approach
                    if cloudflare_detected:
                        if attempt < max_retries:
                            self.logger.info(f"Retrying with different approach (attempt {attempt+1}/{max_retries})")
                            await browser.close()
                            await asyncio.sleep(5)  # Wait before retry
                            continue
                        else:
                            self.logger.error("All attempts to bypass Cloudflare failed")
                            return None
                    
                    # Try multiple selectors to find the price - prioritize the vtex selector which works
                    selectors = [
                        '.vtex-product-price-1-x-sellingPriceValue',  # This is the one that works
                        '.vtex-product-price-1-x-currencyContainer',
                        '.vtex-product-price-1-x-sellingPrice',
                        '.product-price',
                        '.product-price__wrapper',
                        '.price-tag-text',
                        '.price',
                        '.price-best-price',
                        '[data-testid="price"]',
                        '.product__price'
                    ]
                    
                    price = await self.extract_price_with_selectors(page, selectors)
                    
                    # If no price found with selectors, try JavaScript evaluation first
                    if not price:
                        self.logger.info("Trying to find price with JavaScript evaluation...")
                        try:
                            price_js = await page.evaluate("""
                                () => {
                                    // Look specifically for the vtex price element
                                    const vtexPrice = document.querySelector('.vtex-product-price-1-x-sellingPriceValue');
                                    if (vtexPrice) {
                                        return vtexPrice.textContent;
                                    }
                                    return null;
                                }
                            """)
                            
                            if price_js:
                                self.logger.info(f"Found price via JavaScript: {price_js}")
                                price = self._extract_price_from_text(price_js)
                                if price is not None:
                                    self.logger.info(f"Successfully extracted price via JavaScript: {price} ARS")
                                    await browser.close()
                                    return price
                        except Exception as js_error:
                            self.logger.error(f"JavaScript evaluation failed: {js_error}")
                    
                    # If JavaScript evaluation fails, try to extract from entire page content
                    if not price:
                        self.logger.info("Trying to extract price from entire page content...")
                        try:
                            content = await page.content()
                            # Look for price patterns in the HTML
                            price_patterns = [
                                r'\$\s*(\d+(?:[.,]\d+)*)',  # $199.999
                                r'precio[^\d]+(\d+(?:[.,]\d+)*)',  # precio: 199.999
                                r'price[^\d]+(\d+(?:[.,]\d+)*)',   # price: 199.999
                                r'valor[^\d]+(\d+(?:[.,]\d+)*)'    # valor: 199.999
                            ]
                            
                            for pattern in price_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                if matches:
                                    self.logger.info(f"Found price matches with pattern {pattern}: {matches}")
                                    # Take the first match and clean it
                                    price_str = re.sub(r'[.,]', '', matches[0])
                                    if price_str.isdigit():
                                        price = float(price_str)
                                        self.logger.info(f"Successfully extracted price from content: {price} ARS")
                                        await browser.close()
                                        return price
                        except Exception as content_error:
                            self.logger.error(f"Content extraction failed: {content_error}")
                    
                    # If we found a price, return it
                    if price:
                        await browser.close()
                        return price
                    
                    # If we didn't find a price but didn't hit Cloudflare, try again if we have attempts left
                    if attempt < max_retries:
                        self.logger.info(f"No price found, retrying (attempt {attempt+1}/{max_retries})")
                        await browser.close()
                        await asyncio.sleep(3)  # Wait before retry
                    else:
                        self.logger.error("All attempts to extract price failed")
                        await browser.close()
                        return None
                except Exception as nav_error:
                    self.logger.error(f"Navigation error on attempt {attempt}: {nav_error}")
                    if attempt < max_retries:
                        self.logger.info(f"Retrying due to navigation error (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(3)  # Wait before retry
                    else:
                        self.logger.error("All attempts failed due to navigation errors")
                        return None
            except Exception as e:
                self.logger.error(f"Error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    self.logger.info(f"Retrying after error (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(3)  # Wait before retry
                else:
                    self.logger.error("All attempts failed due to errors")
                    return None
        
        # If we've exhausted all retries
        self.logger.error("Failed to extract price from Nike Argentina after all retries")
        return None
    
    async def _scrape_us(self, playwright, url: str) -> float:
        """Scrape price from Nike US"""
        if not url:
            self.logger.error("No URL provided for Nike US")
            raise ValueError("No URL provided for Nike US")
        
        self.logger.info(f"Scraping Nike US: {url}")
        price = None
        
        try:
            # Create browser context for US
            browser, context, page = await self.create_browser_context(playwright, 'US')
            
            # Add cookies for Nike US
            await context.add_cookies([{
                'name': 'acceptedCookies',
                'value': 'true',
                'domain': '.nike.com',
                'path': '/'
            }])
            
            # Navigate to the URL with increased timeout
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')
            
            # Wait for network to be idle
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception as e:
                self.logger.warning(f"Network idle timeout, continuing anyway: {e}")
            
            # Additional wait time to ensure JavaScript loads
            await asyncio.sleep(2)
            
            # Take screenshot if debugging is enabled
            await self.take_screenshot(page, 'nike_us')
            
            # Try to find the price with multiple selectors
            selectors = [
                '[data-test="product-price"]',
                '.product-price',
                '.css-b9fpep',  # Common Nike price class
                '.css-1eqfhge',  # Another common Nike price class
                '.css-12whm6j',  # Another price class
                '[data-testid="product-price"]',
                '.product-price__wrapper',
                '.price',
                '.price-tag-text',
                '.price-best-price'
            ]
            
            price = await self.extract_price_with_selectors(page, selectors)
            
            # If no price found with selectors, try JavaScript evaluation
            if not price:
                self.logger.info("Trying to extract price using JavaScript evaluation...")
                try:
                    price_js = await page.evaluate("""
                        () => {
                            // Look for price elements with specific data attributes
                            const priceElement = document.querySelector('[data-test="product-price"]');
                            if (priceElement) {
                                return priceElement.textContent;
                            }
                            return null;
                        }
                    """)
                    
                    if price_js:
                        self.logger.info(f"Found price via JavaScript: {price_js}")
                        price = self._extract_price_from_text(price_js)
                        if price is not None:
                            self.logger.info(f"Successfully extracted price via JavaScript: {price} USD")
                except Exception as js_error:
                    self.logger.error(f"JavaScript evaluation failed: {js_error}")
            
            # Close browser
            await browser.close()
            
        except Exception as e:
            self.logger.error(f"Error scraping Nike US: {e}")
        
        # If all extraction methods fail, raise an error
        if not price:
            error_msg = "Failed to extract price from Nike US"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        return price
        
    async def extract_price_with_selectors(self, page, selectors: List[str]) -> Optional[float]:
        """Try to extract price using multiple selectors"""
        for selector in selectors:
            try:
                # Try to find the element without waiting first
                price_element = await page.query_selector(selector)
                
                if not price_element:
                    # If not found immediately, wait with a shorter timeout
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        price_element = await page.query_selector(selector)
                    except Exception:
                        # Timeout waiting for selector, continue to next one
                        continue
                
                if price_element:
                    # Try inner_text first
                    try:
                        price_text = await price_element.inner_text()
                        self.logger.info(f"Found price text with selector {selector}: {price_text}")
                        
                        # Extract the price using the appropriate method
                        price = self._extract_price_from_text(price_text)
                        if price is not None:
                            self.logger.info(f"Successfully extracted price: {price}")
                            return price
                    except Exception:
                        # If inner_text fails, try text_content
                        try:
                            price_text = await price_element.text_content()
                            self.logger.info(f"Found price text (text_content) with selector {selector}: {price_text}")
                            
                            # Extract the price using the appropriate method
                            price = self._extract_price_from_text(price_text)
                            if price is not None:
                                self.logger.info(f"Successfully extracted price: {price}")
                                return price
                        except Exception as text_error:
                            self.logger.warning(f"Failed to get text from element: {text_error}")
            except Exception as e:
                self.logger.warning(f"Selector {selector} failed: {e}")
        
        # If all selectors fail, try evaluating JavaScript to find prices
        try:
            self.logger.info("Trying to find price with JavaScript evaluation...")
            price_js = await page.evaluate("""
                () => {
                    // Look for any element containing a dollar sign and a number
                    const priceRegex = /\$\s*\d+([.,]\d+)?/;
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.textContent && priceRegex.test(el.textContent)) {
                            const text = el.textContent.trim();
                            if (text.length < 20) { // Avoid long text blocks
                                return text;
                            }
                        }
                    }
                    return null;
                }
            """)
            
            if price_js:
                self.logger.info(f"Found price via general JS evaluation: {price_js}")
                price = self._extract_price_from_text(price_js)
                if price is not None:
                    self.logger.info(f"Successfully extracted price via JS: {price}")
                    return price
        except Exception as js_error:
            self.logger.warning(f"JavaScript price extraction failed: {js_error}")
        
        return None
