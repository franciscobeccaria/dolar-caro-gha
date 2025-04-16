from .base_scraper import BaseScraper
from typing import Dict, Any, List, Optional
import asyncio
import re
from playwright.async_api import async_playwright

class AdidasScraper(BaseScraper):
    """Scraper for Adidas products"""
    
    def __init__(self, debug: bool = False, screenshots_dir: str = None):
        super().__init__(debug, screenshots_dir)
        self.product_urls = {
            # Argentina Anniversary Jersey
            'argentina_jersey': {
                'AR': "https://www.adidas.com.ar/camiseta-aniversario-50-anos-seleccion-argentina/JF0395.html",
                'US': "https://www.adidas.com/us/argentina-anniversary-jersey/JF2641.html"
            }
            # Add more products as needed
        }
        
        # No fallback prices - we'll raise errors instead
    
    async def scrape(self, product_key: str = 'argentina_jersey') -> Dict[str, Any]:
        """Scrape prices for an Adidas product"""
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
        """Scrape price from Adidas Argentina"""
        if not url:
            self.logger.error("No URL provided for Adidas Argentina")
            raise ValueError("No URL provided for Adidas Argentina")
        
        self.logger.info(f"Scraping Adidas Argentina: {url}")
        price = None
        
        try:
            # Create browser context for Argentina
            browser, context, page = await self.create_browser_context(playwright, 'AR')
            
            # Add cookies for Adidas Argentina
            await context.add_cookies([{
                'name': 'accept_cookies',
                'value': 'true',
                'domain': '.adidas.com.ar',
                'path': '/'
            }])
            
            # Set extra headers specific to Adidas
            await page.set_extra_http_headers({
                'Accept-Language': 'es-AR,es;q=0.9',
                'Referer': 'https://www.adidas.com.ar/ropa-seleccion-argentina',
                'Sec-Ch-Ua': '"Chromium";v="122", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"'
            })
            
            # Navigate to the URL with more robust handling
            try:
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                # First wait for domcontentloaded, then try to wait for networkidle with a shorter timeout
                try:
                    await page.wait_for_load_state('networkidle', timeout=5000)
                except Exception as load_error:
                    self.logger.warning(f"Network idle timeout, continuing anyway: {load_error}")
                
                # Additional wait time to ensure JavaScript loads
                await asyncio.sleep(3)
                
                # Take screenshot if debugging is enabled
                await self.take_screenshot(page, 'adidas_ar')
            except Exception as nav_error:
                self.logger.error(f"Navigation error: {nav_error}")
            
            # Try to directly find the main-price element first
            try:
                self.logger.info("Trying to find element with data-testid=main-price directly")
                main_price_element = await page.query_selector('[data-testid="main-price"]')
                if main_price_element:
                    main_price_text = await main_price_element.inner_text()
                    self.logger.info(f"Found main-price element with text: {main_price_text}")
                    # Try to extract the price from this text
                    price = self._extract_price_from_text(main_price_text)
                    if price is not None:
                        self.logger.info(f"Successfully extracted price from main-price: {price}")
                        return price
                else:
                    self.logger.info("No element with data-testid=main-price found")
                    
                # Try to evaluate JavaScript to find the main-price
                main_price_js = await page.evaluate("""
                    () => {
                        const mainPriceEl = document.querySelector('[data-testid="main-price"]');
                        if (mainPriceEl) {
                            return {
                                text: mainPriceEl.textContent,
                                html: mainPriceEl.innerHTML,
                                exists: true
                            };
                        }
                        return { exists: false };
                    }
                """)
                
                self.logger.info(f"JavaScript evaluation for main-price: {main_price_js}")
                
                if main_price_js.get('exists'):
                    price = self._extract_price_from_text(main_price_js.get('text', ''))
                    if price is not None:
                        self.logger.info(f"Successfully extracted price from main-price via JS: {price}")
                        return price
            except Exception as e:
                self.logger.error(f"Error trying to find main-price element: {e}")
            
            # Fall back to other selectors if main-price didn't work
            selectors = [
                '[data-testid="main-price"]',  # Try again with normal selector approach
                '[data-testid="product-price"]',
                '[data-testid="price-component"]',
                'div.gl-price-item--sale',  # For sale prices
                '.product-price-container .price',
                '.product-price',
                '.gl-price-item',
                '.gl-price__value',
                '[data-auto-id="product-price"]',
                '[data-auto-id="sale-price"]'
            ]
            
            price = await self.extract_price_with_selectors(page, selectors)
            
            # If no price found with selectors, try to extract from entire page content
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
                                break
                except Exception as content_error:
                    self.logger.error(f"Content extraction failed: {content_error}")
            
            # Close browser
            await browser.close()
            
        except Exception as e:
            self.logger.error(f"Error scraping Adidas Argentina: {e}")
        
        # If all extraction methods fail, raise an error
        if not price:
            error_msg = "Failed to extract price from Adidas Argentina"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        return price
    
    async def _scrape_us(self, playwright, url: str) -> float:
        """Scrape price from Adidas US"""
        if not url:
            self.logger.error("No URL provided for Adidas US")
            raise ValueError("No URL provided for Adidas US")
        
        self.logger.info(f"Scraping Adidas US: {url}")
        price = None
        
        try:
            # Create browser context for US
            browser, context, page = await self.create_browser_context(playwright, 'US')
            
            # Add cookies for Adidas US
            await context.add_cookies([{
                'name': 'geo_country',
                'value': 'US',
                'domain': '.adidas.com',
                'path': '/'
            }, {
                'name': 'languageLocale',
                'value': 'en_US',
                'domain': '.adidas.com',
                'path': '/'
            }])
            
            # Set extra headers specific to Adidas
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.adidas.com/us/soccer-jerseys',
                'Sec-Ch-Ua': '"Chromium";v="122", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"'
            })
            
            # Navigate to the URL with more robust handling
            try:
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                # First wait for domcontentloaded, then try to wait for networkidle with a shorter timeout
                try:
                    await page.wait_for_load_state('networkidle', timeout=5000)
                except Exception as load_error:
                    self.logger.warning(f"Network idle timeout, continuing anyway: {load_error}")
                
                # Additional wait time to ensure JavaScript loads
                await asyncio.sleep(3)
                
                # Take screenshot if debugging is enabled
                await self.take_screenshot(page, 'adidas_us')
            except Exception as nav_error:
                self.logger.error(f"Navigation error: {nav_error}")
            
            # Try to directly find the main-price element first
            try:
                self.logger.info("Trying to find element with data-testid=main-price directly for US site")
                main_price_element = await page.query_selector('[data-testid="main-price"]')
                if main_price_element:
                    main_price_text = await main_price_element.inner_text()
                    self.logger.info(f"Found main-price element with text: {main_price_text}")
                    # Try to extract the price from this text
                    price = self._extract_price_from_text(main_price_text)
                    if price is not None:
                        self.logger.info(f"Successfully extracted price from main-price: {price}")
                        return price
                else:
                    self.logger.info("No element with data-testid=main-price found in US site")
                    
                # Try to evaluate JavaScript to find the main-price
                main_price_js = await page.evaluate("""
                    () => {
                        const mainPriceEl = document.querySelector('[data-testid="main-price"]');
                        if (mainPriceEl) {
                            return {
                                text: mainPriceEl.textContent,
                                html: mainPriceEl.innerHTML,
                                exists: true
                            };
                        }
                        
                        // Try to find any element with data-testid containing 'price'
                        const priceElements = Array.from(document.querySelectorAll('[data-testid*="price"]'));
                        if (priceElements.length > 0) {
                            return {
                                elements: priceElements.map(el => ({
                                    testid: el.getAttribute('data-testid'),
                                    text: el.textContent,
                                    html: el.innerHTML
                                })),
                                exists: false
                            };
                        }
                        
                        return { exists: false };
                    }
                """)
                
                self.logger.info(f"JavaScript evaluation for main-price in US site: {main_price_js}")
                
                if main_price_js.get('exists'):
                    price = self._extract_price_from_text(main_price_js.get('text', ''))
                    if price is not None:
                        self.logger.info(f"Successfully extracted price from main-price via JS: {price}")
                        return price
                elif main_price_js.get('elements'):
                    self.logger.info(f"Found other price elements: {main_price_js.get('elements')}")
                    for element in main_price_js.get('elements', []):
                        price = self._extract_price_from_text(element.get('text', ''))
                        if price is not None:
                            self.logger.info(f"Successfully extracted price from {element.get('testid')}: {price}")
                            return price
            except Exception as e:
                self.logger.error(f"Error trying to find main-price element in US site: {e}")
            
            # Fall back to other selectors if main-price didn't work
            selectors = [
                '[data-testid="main-price"]',  # Try again with normal selector approach
                '[data-testid="product-price"]',
                '[data-testid="price-component"]',
                'div.gl-price-item--sale',  # For sale prices
                '.gl-price-item',
                '.gl-price__value',
                '[data-auto-id="product-price"]',
                '[data-auto-id="sale-price"]',
                '.product-price'
            ]
            
            price = await self.extract_price_with_selectors(page, selectors)
            
            # If no price found with selectors, try JavaScript evaluation
            if not price:
                self.logger.info("Trying to extract price using JavaScript evaluation...")
                try:
                    # Try to extract price using JavaScript evaluation
                    price_js = await page.evaluate('''
                        () => {
                            // Look for price in data-testid attributes first (most reliable)
                            const testIdElements = document.querySelectorAll('[data-testid="product-price"], [data-testid="price-component"], [data-testid="main-price"]');
                            for (const el of testIdElements) {
                                const price = el.textContent;
                                if (price && price.includes('$')) {
                                    return price;
                                }
                            }
                            
                            // Look for price in sale item elements
                            const saleElements = document.querySelectorAll('div.gl-price-item--sale');
                            for (const el of saleElements) {
                                const price = el.textContent;
                                if (price && price.includes('$')) {
                                    return price;
                                }
                            }
                            
                            // Look for price in window.adobeDataLayer
                            if (window.adobeDataLayer) {
                                for (const item of window.adobeDataLayer) {
                                    if (item.product && item.product.price) {
                                        return item.product.price;
                                    }
                                }
                            }
                            
                            // Then try auto-id attributes
                            const autoIdElements = document.querySelectorAll('[data-auto-id="product-price"], [data-auto-id="sale-price"]');
                            for (const el of autoIdElements) {
                                const price = el.textContent;
                                if (price && price.includes('$')) {
                                    return price;
                                }
                            }
                            
                            // Last resort - look for any element with a price
                            const allElements = document.querySelectorAll('*');
                            for (const el of allElements) {
                                if (el.textContent && el.textContent.includes('$') && /\$\s*\d+/.test(el.textContent)) {
                                    const text = el.textContent.trim();
                                    if (text.length < 20) { // Avoid long text blocks
                                        return text;
                                    }
                                }
                            }
                            return null;
                        }
                    ''')
                    
                    if price_js:
                        self.logger.info(f"Found price via JavaScript: {price_js}")
                        price_match = re.search(r'\$\s*(\d+(?:\.\d+)?)', price_js)
                        if price_match:
                            price = float(price_match.group(1))
                            self.logger.info(f"Successfully extracted price via JavaScript: ${price} USD")
                except Exception as js_error:
                    self.logger.error(f"JavaScript evaluation failed: {js_error}")
            
            # Close browser
            await browser.close()
            
        except Exception as e:
            self.logger.error(f"Error scraping Adidas US: {e}")
        
        # If all extraction methods fail, raise an error
        if not price:
            error_msg = "Failed to extract price from Adidas US"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        return price
        
    async def extract_price_with_selectors(self, page, selectors: List[str]) -> Optional[float]:
        """Try to extract price using multiple selectors"""
        for selector in selectors:
            try:
                self.logger.info(f"Trying selector: {selector}")
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
        
        return None
