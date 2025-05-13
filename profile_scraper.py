from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import logging
import pandas as pd
import time
import os
import pickle
import random
# Add import at the top
import pprint
# Add at the top with other imports
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ProfileScraper:
    def __init__(self, data_dir, headless=True):
        self.data_dir = data_dir
        self.profile_data = []
        self.driver = self.init_driver(headless)
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(data_dir, exist_ok=True)

    def init_driver(self, headless):
        options = uc.ChromeOptions()
        
        # Anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--window-size=1920,1080')
        
        # Random user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        if headless:
            options.add_argument('--headless=new')
            
        return uc.Chrome(options=options)

    def load_cookies(self, filename):
        with open(filename, 'rb') as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                self.driver.add_cookie(cookie)

    def handle_authentication(self):
        cookie_file = os.path.join(self.data_dir, 'cookies.pkl')
        
        # Check for existing valid cookies
        if os.path.exists(cookie_file):
            try:
                if os.path.getsize(cookie_file) > 0:
                    self.load_cookies(cookie_file)
                    self.logger.info('Using existing cookies')
                    return False
                else:
                    self.logger.warning('Empty cookies file detected')
                    os.remove(cookie_file)
            except (EOFError, pickle.UnpicklingError):
                self.logger.error('Corrupted cookies file')
                os.remove(cookie_file)
    
        # If no valid cookies, perform fresh authentication
        self.driver.get('https://signal.nfx.com/login')
        self.logger.info('Please manually log in within 2 minutes...')
        
        # Wait for successful authentication
        start_time = time.time()
        while time.time() - start_time < 120:
            if 'investors' in self.driver.current_url:
                self.save_cookies(cookie_file)
                self.logger.info('Login successful, cookies saved')
                return True
            time.sleep(5)
        
        raise TimeoutError('Authentication timed out')
    
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        
        self.save_cookies(cookie_file)
        
        if os.path.getsize(cookie_file) == 0:
            raise RuntimeError('Failed to save valid cookies')
        
        return True
    
    def save_cookies(self, filename):
        cookies = self.driver.get_cookies()
        if not cookies:
            self.logger.warning('No cookies to save')
            return
        
        with open(filename, 'wb') as file:
            pickle.dump(cookies, file)
        self.logger.info(f'Saved {len(cookies)} cookies to {filename}')

    def extract_profile_data(self, soup):
        profile = {
            'name': '',
            'current_company': '',
            'investment_range': '',
            'investments_on_record': '',
            'sweet_spot': '',
            'current_fund_size': '',
            'experience': [],
            'sector_rankings': [],
            'social_links': {},
            'network_memberships': [],
            'education': [],
            'all_previous_investments': []
        }

        # Extract investment stats with safe element access
        for row in soup.select('.line-separated-row.row'):
            label_elem = row.select_one('.col-xs-5 .lh-solid')
            value_elem = row.select_one('.col-xs-7 .lh-solid')
            
            if label_elem and value_elem:
                label = label_elem.text.strip(':')
                value = value_elem.text.strip()
                
                if 'Current Investing Position' in label:
                    profile['current_company'] = value.split(' at ')[-1] if ' at ' in value else value
                elif 'Investment Range' in label:
                    profile['investment_range'] = value
                elif 'Sweet Spot' in label:
                    profile['sweet_spot'] = value
                elif 'Current Fund Size' in label:
                    profile['current_fund_size'] = value
                elif 'Investments On Record' in label:
                    profile['investments_on_record'] = value

        # Safe name extraction
        name_tag = soup.select_one('.identity-block h1')
        profile['name'] = name_tag.get_text(strip=True).split('(')[0].strip() if name_tag else ''
    
        # Safe current company extraction
        current_company_span = soup.find('span', class_='section-label lh-solid', string='Current Investing Position')
        if current_company_span:
            company_div = current_company_span.find_parent('div').find_next_sibling('div', class_='col-xs-7')
            if company_div:
                company_link = company_div.find('a')
                profile['current_company'] = company_link.get_text(strip=True) if company_link else company_div.get_text(strip=True)

        # Safe experience extraction
        for exp in soup.select('.line-separated-row.flex.justify-between'):
            parts = exp.get_text(separator='|', strip=True).split('|')
            if len(parts) >= 3:
                profile['experience'].append({
                    'role': parts[0],
                    'company': parts[1],
                    'duration': parts[-1]
                })
    
        # Safe sector rankings
        profile['sector_rankings'] = [
            a.text.strip() 
            for section in soup.select('div.sn-margin-top-30.relative') 
            if 'Sector & Stage Rankings' in section.text
            for a in section.select('a.vc-list-chip')
        ]
    
        # Safe social links
        links_container = soup.select_one('.sn-linkset')
        if links_container:
            for link in links_container.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com' in href:
                    profile['social_links']['linkedin'] = href
                elif 'twitter.com' in href:
                    profile['social_links']['twitter'] = href
                elif 'angel.co' in href:
                    profile['social_links']['angellist'] = href
                elif 'crunchbase.com' in href:
                    profile['social_links']['crunchbase'] = href
                elif not any(x in href for x in ['linkedin', 'twitter', 'angel', 'crunchbase']):
                    profile['social_links']['website'] = href

        # Safe network memberships
        for network in soup.select('.mt2'):
            name = network.select_one('.f6')
            count = network.select_one('.f7')
            if name and count:
                profile['network_memberships'].append({
                    'network_name': name.text.strip(),
                    'connection_count': ''.join(filter(str.isdigit, count.text))
                })

        # Safe education
        for network in soup.select('.mt2'):
            name = network.select_one('.f6')
            if name and ('university' in name.text.lower() or 'school' in name.text.lower()):
                profile['education'].append({
                    'school': name.text.strip(),
                    'degree': 'Not specified',
                    'year': 'Not specified'
                })

        # Safe investment data
        for row in soup.select('tbody.past-investments-table-body tr'):
            if 'coinvestors-row' not in row.get('class', []):
                investment = {}
                company = row.select_one('td.with-coinvestors div.round-padding')
                investment['company'] = company.text.strip() if company else ''
                
                stages = row.select('td.with-coinvestors div.round-padding')
                if stages and len(stages) > 1:
                    try:
                        stage_info = stages[1].text.strip().split('·')
                        if len(stage_info) >= 3:
                            investment['stage'] = stage_info[0].strip()
                            investment['date'] = stage_info[1].strip()
                            investment['round_size'] = stage_info[2].strip()
                    except (IndexError, AttributeError):
                        pass
                
                total_raised = row.select_one('td.with-coinvestors:nth-child(3) div.round-padding')
                investment['total_raised'] = total_raised.text.strip() if total_raised else ''
                
                if any(investment.values()):
                    profile['all_previous_investments'].append(investment)
        
        self.logger.debug(f'Extracted profile data:\n{pprint.pformat(profile)}')
        return profile

    def save_profiles(self):
        if not self.profile_data:
            return

        df = pd.DataFrame(self.profile_data)
        output_file = os.path.join(self.data_dir, 'investor_profiles.csv')
        df.to_csv(output_file, index=False, mode='a', header=not os.path.exists(output_file))
        self.logger.info(f'Saved {len(df)} profiles to {output_file}')

    def save_error(self, url, error):
        error_file = os.path.join(self.data_dir, 'scraper_errors.csv')
        pd.DataFrame([{
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'url': url,
            'error': error
        }]).to_csv(error_file, mode='a', header=not os.path.exists(error_file))

    def random_sleep(self, min, max):
        time.sleep(random.uniform(min, max))

    def __del__(self):
        self.safe_quit_driver()

    def safe_quit_driver(self):
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f'Driver quit error: {str(e)}')
            finally:
                self.driver = None
                
    def scrape_profile(self, profile_url):
        # Create profile file path before scraping
        profile_file = os.path.join(self.data_dir, f"profile_scper_data.csv")
        
        try:
            # Initialize empty profile file
            pd.DataFrame(columns=['url', 'timestamp', 'status']).to_csv(profile_file, index=False)
            
            self.driver.get(profile_url)
            self.random_sleep(3, 5)
            
            # Handle authentication if needed
            if self.handle_authentication():
                self.driver.get(profile_url)
                self.random_sleep(3, 5)
    
            # Alternative button handling using JavaScript execution
            try:
                # Update XPath to match button text pattern
                button = self.driver.find_element(
                    By.XPATH,
                    '//button[starts-with(normalize-space(), "See all") '
                    'and contains(., "investments on record")]'
                )
                
                # Store initial investment count
                initial_investments = len(self.driver.find_elements(
                    By.CSS_SELECTOR, 'tbody.past-investments-table-body tr'
                ))
                
                # Click using JavaScript to bypass visibility issues
                self.driver.execute_script("arguments[0].click();", button)
                
                # Wait for investments to load using expected conditions
                WebDriverWait(self.driver, 15).until(
                    lambda d: len(d.find_elements(
                        By.CSS_SELECTOR, 'tbody.past-investments-table-body tr'
                    )) > initial_investments
                )
                
                self.logger.info('Successfully loaded additional investments')
                
            except Exception as e:
                self.logger.warning(f'Alternative button handling failed: {str(e)}')
                # Fallback to direct API call simulation
                try:
                    self.driver.execute_script(
                        "fetch('/investors/load_more_investments', {"
                        "method: 'POST',"
                        "headers: {'Content-Type': 'application/json'}, "
                        "body: JSON.stringify({investor_id: 4109}) "
                        "})"
                    )
                    self.random_sleep(2, 3)
                except Exception as api_error:
                    self.logger.error(f'API fallback failed: {str(api_error)}')

            # Parse the updated page source
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            profile = self.extract_profile_data(soup)
            profile.update({
                'url': profile_url,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            self.profile_data.append(profile)
            print('\nSuccessfully scraped profile:')
            pprint.pprint(profile)
            self.logger.info(f'Successfully scraped: {profile_url}')

            # After successful scrape
            profile.update({
                'url': profile_url,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'success'
            })
            
            # Save to pre-created profile file
            pd.DataFrame([profile]).to_csv(profile_file, index=False)
            
            # Also append to main CSV
            self.save_profiles()
            
            # Update progress tracking
            progress_file = os.path.join(self.data_dir, 'progress.csv')
            progress_data = {
                'url': [profile_url],
                'status': ['success'],
                'timestamp': [time.strftime('%Y-%m-%d %H:%M:%S')],
                'file_path': [profile_file]
            }
            
            if os.path.exists(progress_file):
                pd.DataFrame(progress_data).to_csv(progress_file, mode='a', header=False, index=False)
            else:
                pd.DataFrame(progress_data).to_csv(progress_file, index=False)
                
        except Exception as e:
            # Update progress with failure
            progress_file = os.path.join(self.data_dir, 'progress.csv')
            progress_data = {
                'url': [profile_url],
                'status': ['failed'],
                'error': [str(e)],
                'timestamp': [time.strftime('%Y-%m-%d %H:%M:%S')]
            }
            
            if os.path.exists(progress_file):
                pd.DataFrame(progress_data).to_csv(progress_file, mode='a', header=False, index=False)
            else:
                pd.DataFrame(progress_data).to_csv(progress_file, index=False)
            
            self.logger.error(f'Failed to scrape {profile_url}: {str(e)}')
            self.save_error(profile_url, str(e))

class SitemapScraper:
    def __init__(self, file_path='sitemap.xml/sitemap.xml'):
        self.file_path = file_path
        self.investor_links = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_local_sitemap(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                sitemap_content = f.read()
            soup = BeautifulSoup(sitemap_content, 'xml')
            self.investor_links = [
                loc.text.strip()
                for loc in soup.find_all('loc')
                if '/investors/' in loc.text
                and not loc.text.startswith('https://signal.nfx.com/investors/#signin')
            ]
            self.logger.info(f'Found {len(self.investor_links)} investor profiles in sitemap')
            return True
        except Exception as e:
            self.logger.error(f'Sitemap parsing failed: {str(e)}')
            return False

    def get_investor_links(self, limit=None):
        if limit:
            return self.investor_links[:limit]
        return self.investor_links

if __name__ == '__main__':
    # Initialize profile scraper FIRST
    scraper = ProfileScraper(data_dir=os.getcwd(), headless=False)
    
    # Initialize and parse sitemap
    sitemap_scraper = SitemapScraper()
    if sitemap_scraper.parse_local_sitemap():
        investor_urls = sitemap_scraper.get_investor_links()
        total_links = len(investor_urls)
        
        print(f"Found {total_links} investor links in sitemap")
        # Now use the properly initialized scraper
        scraper.logger.info(f"\n{'='*40}\nStarting scrape of {total_links} investor profiles\n{'='*40}")
        
        successful_scrapes = 0

        # In the main scraping loop, add more detailed error handling:
        for i, url in enumerate(investor_urls, 1):
            try:
                scraper.logger.info(f"Scraping URL {i}/{total_links}")
                scraper.scrape_profile(url)
                successful_scrapes += 1
            except Exception as e:
                scraper.logger.error(f"Failed to scrape {url}")
                scraper.logger.error(f"Error details: {str(e)}")
                scraper.logger.error(f"Page source saved to debug.html")
                with open("debug.html", "w", encoding="utf-8") as f:
                    f.write(scraper.driver.page_source)
                scraper.save_error(url, str(e))
            finally:
                scraper.random_sleep(5, 10)
                
        # Completion summary
        scraper.logger.info(f"\n{'='*40}\nScraping completed!\n"
                          f"Successfully scraped: {successful_scrapes}/{total_links}\n"
                          f"Failed: {total_links - successful_scrapes}\n"
                          f"Results saved to: investor_profiles.csv\n"
                          f"Errors logged to: scraper_errors.csv\n"
                          f"{'='*40}")
        
        scraper.save_profiles()
        scraper.safe_quit_driver()