import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time
import logging
from typing import List, Dict
import xml.etree.ElementTree as ET
import os
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import base64
from cryptography.fernet import Fernet
from contextlib import contextmanager

# Set up logging with more detailed format
output_dir = os.path.join(os.getcwd(), 'output', 'logs')
os.makedirs(output_dir, exist_ok=True)
log_file = os.path.join(output_dir, f'scraper_{time.strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

class SitemapScraper:
    def __init__(self, sitemap_path: str, delay: float = 1.0):
        """
        Initialize the scraper with sitemap path and delay between requests
        
        Args:
            sitemap_path (str): Path to the sitemap file
            delay (float): Delay between requests in seconds
        """
        self.sitemap_path = sitemap_path
        self.delay = delay
        
        # Create output directory structure
        self.output_dir = os.path.join(os.getcwd(), 'output')
        self.data_dir = os.path.join(self.output_dir, 'data')
        self.logs_dir = os.path.join(self.output_dir, 'logs')
        self.cookies_dir = os.path.join(self.output_dir, 'cookies')
        
        # Create directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.cookies_dir, exist_ok=True)
        
        # Update file paths
        self.cookies_file = os.path.join(self.cookies_dir, 'cookies.enc')
        self.key_file = os.path.join(self.cookies_dir, 'key.key')
        
        # Generate or load encryption key
        if not os.path.exists(self.key_file):
            self.key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(self.key)
        else:
            with open(self.key_file, 'rb') as f:
                self.key = f.read()
        
        self.cipher_suite = Fernet(self.key)
        
        # Set up Chrome options with enhanced anti-detection
        options = uc.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--window-size=1920,1080')
        
        # Add random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Initialize the Chrome driver with service
        service = Service(ChromeDriverManager().install())
        self.driver = uc.Chrome(options=options, service=service)
        self.driver.set_page_load_timeout(30)
        
        logger.info(f"Initialized scraper with sitemap path: {sitemap_path}")

    @contextmanager
    def managed_driver(self):
        """Context manager for the Chrome driver"""
        try:
            yield self.driver
        except Exception as e:
            logger.error(f"Error in managed driver: {str(e)}")
            raise
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    # Give some time for the driver to clean up
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")
                # Force cleanup if normal quit fails
                try:
                    if hasattr(self.driver, 'service') and self.driver.service.process:
                        self.driver.service.process.kill()
                except:
                    pass

    def save_cookies(self):
        """Save cookies to an encrypted file"""
        try:
            cookies = self.driver.get_cookies()
            encrypted_data = self.cipher_suite.encrypt(json.dumps(cookies).encode())
            with open(self.cookies_file, 'wb') as f:
                f.write(encrypted_data)
            logger.info("Cookies saved successfully")
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")

    def load_cookies(self):
        """Load cookies from encrypted file"""
        try:
            if not os.path.exists(self.cookies_file):
                logger.warning("No cookies file found")
                return False
                
            with open(self.cookies_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            cookies = json.loads(decrypted_data)
            
            # Navigate to base domain before adding cookies
            self.driver.get("https://signal.nfx.com")
            
            for cookie in cookies:
                if 'expiry' in cookie and cookie['expiry'] is None:
                    del cookie['expiry']
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not add cookie: {cookie.get('name', '')}: {e}")
            
            logger.info("Cookies loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading cookies: {str(e)}")
            return False

    def export_cookies_from_browser(self):
        """Guide user to export cookies from their browser"""
        print("\n=== Cookie Export Instructions ===")
        print("1. Open Chrome and go to signal.nfx.com")
        print("2. Log in to your account")
        print("3. Press F12 to open Developer Tools")
        print("4. Go to 'Application' tab")
        print("5. In the left sidebar, expand 'Cookies'")
        print("6. Click on 'https://signal.nfx.com'")
        print("7. Right-click on any cookie and select 'Copy all'")
        print("8. Create a new file named 'cookies.txt' and paste the cookies there")
        print("9. Save the file in the same directory as this script")
        print("===============================\n")
        
        input("Press Enter after you have saved the cookies.txt file...")
        
        try:
            with open('cookies.txt', 'r') as f:
                cookie_data = f.read()
            
            # Parse cookies from the text file
            cookies = []
            for line in cookie_data.split('\n'):
                if line.strip():
                    try:
                        name, value = line.split('\t')[:2]
                        cookies.append({
                            'name': name.strip(),
                            'value': value.strip(),
                            'domain': '.signal.nfx.com'
                        })
                    except:
                        continue
            
            # Save cookies in pickle format
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            print("Cookies successfully imported!")
            return True
        except Exception as e:
            print(f"Error importing cookies: {str(e)}")
            return False

    def handle_authentication(self):
        """Handle the authentication process safely and persistently."""
        try:
            # Check if we're on the login page
            if ("Continue With Google" in self.driver.page_source or "sign up or log in" in self.driver.page_source or "LOGIN" in self.driver.page_source):
                logger.info("Authentication required. Please log in manually...")
                print("\n=== Login Required ===")
                print("A browser window will open. Please log in to your account.")
                print("After logging in, come back here and press Enter.")
                print("=====================\n")
                input("Press Enter to open the browser window...")
                self.driver.get("https://signal.nfx.com/login")
                self.random_sleep()
                input("Please log in in the browser window and press Enter when done...")
                # Verify login was successful
                if ("Continue With Google" in self.driver.page_source or "sign up or log in" in self.driver.page_source or "LOGIN" in self.driver.page_source):
                    logger.error("Login failed. Please try again.")
                    return False
                # Save cookies after successful login
                self.save_cookies()
                logger.info("Login successful, cookies saved")
                return True
            return False
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False

    def get_sitemap_urls(self) -> List[str]:
        """Extract URLs from the local sitemap file"""
        try:
            logger.info(f"Reading sitemap file from: {self.sitemap_path}")
            # Parse local XML file
            tree = ET.parse(self.sitemap_path)
            root = tree.getroot()
            
            # Extract URLs (handling both standard sitemap and sitemap index)
            urls = []
            for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                if 'signal.nfx.com/investor-lists' in url.text:
                    urls.append(url.text)
                    logger.debug(f"Found investor list URL: {url.text}")
            
            logger.info(f"Found {len(urls)} investor list URLs in sitemap")
            if len(urls) == 0:
                logger.warning("No investor list URLs found in sitemap!")
            return urls
        except Exception as e:
            logger.error(f"Error parsing sitemap: {str(e)}")
            return []

    def random_sleep(self, min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Sleep for a random amount of time to appear more human-like"""
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)

    def extract_investor_data(self, soup: BeautifulSoup) -> List[Dict]:
        investors = []
        try:
            # First find the table containing investor data
            table = soup.find('table')
            if not table:
                logger.warning("No table found on the page")
                return []
    
            # Find all investor rows - they are tr elements containing td with flex div
            investor_rows = table.find_all('tr')
            logger.info(f"Found {len(investor_rows)} investor rows on the page")
            
            for row in investor_rows:
                try:
                    # Get the first td that contains the investor info
                    cell = row.find('td')
                    if not cell:
                        continue
                        
                    investor = self._extract_single_investor(cell)
                    if investor:  # Remove validation check, accept all non-None investors
                        # Add investment range if available
                        range_cell = row.find('td', class_='text-center pt2')
                        if range_cell:
                            investor['investment_range'] = range_cell.get_text(strip=True)
                        else:
                            investor['investment_range'] = ''
                        
                        # Add location and categories
                        location_cell = row.find('td', attrs={'style': 'max-width: 400px;'})
                        if location_cell:
                            investor['locations'] = [a.get_text(strip=True) for a in location_cell.find_all('a')]
                        else:
                            investor['locations'] = []
                        
                        categories_cell = row.find_all('td', attrs={'style': 'max-width: 400px;'})[-1]
                        if categories_cell:
                            investor['categories'] = [a.get_text(strip=True) for a in categories_cell.find_all('a')]
                        else:
                            investor['categories'] = []
                        
                        investors.append(investor)
                except Exception as e:
                    logger.error(f"Error extracting investor row data: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error extracting investor data: {str(e)}")
        
        logger.info(f"Extracted {len(investors)} investors from the page")
        return investors

    def extract_all_visible_text(self, soup: BeautifulSoup) -> str:
        """Extract all visible text from the page, excluding scripts, styles, and hidden elements."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript', 'header', 'footer', 'svg', 'img']):
            element.decompose()
        # Remove hidden elements
        for tag in soup.find_all(style=True):
            if 'display:none' in tag['style'] or 'visibility:hidden' in tag['style']:
                tag.decompose()
        # Get all visible text
        text = soup.get_text(separator=' ', strip=True)
        # Collapse multiple spaces
        import re
        text = re.sub(r'\s+', ' ', text)
        return text

    def scrape_page(self, url: str, max_retries: int = 3) -> tuple:
        """Scrape a page and return both raw text and investor data"""
        all_investors_list = []  # Initialize the list outside the loop
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping page: {url} (Attempt {attempt + 1}/{max_retries})")
                self.load_cookies()
                self.driver.get(url)
                self.random_sleep(5, 8)  # Increased initial wait time
                
                if self.handle_authentication():
                    self.load_cookies()
                    self.driver.get(url)
                    self.random_sleep(5, 8)
                
                # Wait for any content to load first
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Check if we're on a login page
                if "login" in self.driver.current_url.lower():
                    logger.warning("Redirected to login page, attempting to authenticate")
                    if not self.handle_authentication():
                        raise Exception("Authentication failed")
                    self.driver.get(url)
                    self.random_sleep(5, 8)
                
                # Get page source and create soup object
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'lxml')
                
                # Always extract raw text first
                raw_text = self.extract_all_visible_text(soup)
                raw_data = {
                    'url': url,
                    'raw_text': raw_text,
                    'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Try to find table
                table = soup.find('table')
                if not table:
                    logger.info(f"No table found on page: {url}")
                    return raw_data, []
                
                all_investors = set()  # Use a set to track unique investors
                page_num = 1
                
                while True:
                    # Extract investors from current page
                    investors = self.extract_investor_data(soup)
                    if investors:
                        # Create tuples of key fields to identify unique investors
                        for investor in investors:
                            investor_key = (investor['name'], investor['company'], investor['role'])
                            if investor_key not in all_investors:
                                all_investors.add(investor_key)
                                all_investors_list.append(investor)
                        logger.info(f"Extracted {len(investors)} investors from page {page_num} (Total unique: {len(all_investors)})")
                    
                    # Look for 'Load More Investors' button with case-insensitive match
                    load_more = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more investors')]")
                    if not load_more or not load_more[0].is_enabled():
                        break
                    
                    # Click load more and wait
                    load_more[0].click()
                    self.random_sleep(3.0, 5.0)  # Longer delay for loading
                    page_num += 1
                    
                    # Get updated page source
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'lxml')
                
                # Add metadata to investors
                for inv in all_investors_list:
                    inv['source_url'] = url
                    inv['scrape_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                logger.info(f"Total unique investors extracted: {len(all_investors)}")
                return raw_data, all_investors_list
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    self.random_sleep(5.0, 10.0)  # Longer delay between retries
                    continue
                else:
                    logger.error(f"All attempts failed for {url}")
                    # Return raw data even if scraping failed
                    return {
                        'url': url,
                        'raw_text': '',
                        'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'error': str(e)
                    }, []

    def _extract_single_investor(self, cell):
        # try:
        #     investor = {
        #         'name': '',
        #         'company': '',
        #         'role': '',
        #         'profile_url': '',
        #         'company_url': '',
        #         'image_url': ''
        #     }
            
        #     # Find the main div containing investor info
        #     info_div = cell.find('div', class_='flex')
        #     if not info_div:
        #         return None  # Return None for invalid entries instead of empty data
            
        #     # Extract image URL
        #     img_tag = info_div.find('img')
        #     if img_tag and img_tag.get('src'):
        #         investor['image_url'] = img_tag['src']
            
        #     # Find the div containing name and other details
        #     details_div = info_div.find('div', recursive=False)  # Get immediate div child
        #     if details_div:
        #         # Extract name and profile URL
        #         name_link = details_div.find('a', href=lambda x: x and '/investors/' in x)
        #         if name_link:
        #             investor['name'] = name_link.get_text(strip=True)
        #             investor['profile_url'] = 'https://signal.nfx.com' + name_link['href']
                
        #         # Extract company name and URL
        #         company_link = details_div.find('a', href=lambda x: x and '/firms/' in x)
        #         if company_link:
        #             investor['company'] = company_link.get_text(strip=True)
        #             investor['company_url'] = 'https://signal.nfx.com' + company_link['href']
                
        #         # Extract role
        #         role_elem = details_div.find(['span', 'div'], class_=lambda x: x and any(c in x for c in ['role', 'title', 'position']))
        #         if role_elem:
        #             investor['role'] = role_elem.get_text(strip=True)
            
        #     # Only return investor if we found at least name or company
        #     return investor if investor['name'] or investor['company'] else None
            
        # except Exception as e:
        #     logger.error(f"Error extracting investor data: {str(e)}")
        #     return None
        try:
            investor = {
                'name': '',
                'company': '',
                'role': '',
                'profile_url': '',
                'company_url': '',
                'image_url': ''
            }
            
            # Find the main div containing investor info
            info_div = cell.find('div', class_='flex')
            if not info_div:
                return None  # Return None for invalid entries instead of empty data
            
            # Extract image URL
            img_tag = info_div.find('img')
            if img_tag and img_tag.get('src'):
                investor['image_url'] = img_tag['src']
            
            # Extract name
            name_tag = info_div.find('strong', class_='sn-investor-name null')
            if name_tag:
                investor['name'] = name_tag.get_text(strip=True)
                investor['profile_url'] = name_tag.find_parent('a')['href']
            
            # Extract company
            company_tag = info_div.find('a', href=True)
            if company_tag:
                investor['company'] = company_tag.get_text(strip=True)
                investor['company_url'] = company_tag['href']
            
            # Extract role
            role_tag = info_div.find('span', class_='sn-small-link hidden-xs null')
            if role_tag:
                investor['role'] = role_tag.get_text(strip=True)
            
            return investor
        except Exception as e:
            logger.error(f"Error extracting investor data: {str(e)}")
            return None

    def save_to_csv(self, raw_data_list, investors_list):
        try:
            # Convert lists to DataFrames
            raw_df = pd.DataFrame(raw_data_list)
            investors_df = pd.DataFrame(investors_list)
        
            if not raw_df.empty:
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                raw_filename = os.path.join(self.data_dir, f'raw_data_{timestamp}.csv')
                raw_df.to_csv(raw_filename, index=False)
                logger.info(f'Saved {len(raw_df)} raw records to {raw_filename}')
        
            if not investors_df.empty:
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                investors_filename = os.path.join(self.data_dir, f'validinvestors_{timestamp}.csv')
                investors_df.to_csv(investors_filename, index=False)
                logger.info(f'Saved {len(investors_df)} investor records to {investors_filename}')
        
        except Exception as e:
            logger.error(f'Error saving data to CSV: {str(e)}')

    def scrape_all(self, limit: int = None) -> tuple:
        """Scrape all URLs from sitemap up to the specified limit"""
        all_raw_data = []
        all_investors = []
        
        # Get URLs from sitemap
        urls = self.get_sitemap_urls()
        if not urls:
            logger.error("No URLs found in sitemap")
            return [], []
        
        # Apply limit if specified
        if limit:
            urls = urls[:limit]
            logger.info(f"Limiting scrape to first {limit} URLs")
        
        # Scrape each URL
        for url in urls:
            try:
                raw_data, investors = self.scrape_page(url)
                if raw_data:
                    all_raw_data.append(raw_data)
                if investors:
                    all_investors.extend(investors)
                logger.info(f"Successfully scraped {url}")
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue
        
        logger.info(f"Scraping complete. Processed {len(urls)} URLs")
        logger.info(f"Total raw data entries: {len(all_raw_data)}")
        logger.info(f"Total investors found: {len(all_investors)}")
        
        return all_raw_data, all_investors

def main():
    try:
        scraper = SitemapScraper('sitemap.xml\\sitemap.xml')
        raw_df, investors_df = scraper.scrape_all(limit=5)
        if len(raw_df) > 0 or len(investors_df) > 0:
            scraper.save_to_csv(raw_df, investors_df)
        else:
            logger.warning("No data was scraped, skipping CSV save")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == '__main__':
    main()