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

class ProfileScraper:
    def __init__(self, data_dir, headless=True):
        self.data_dir = data_dir
        self.profile_data = []
        self.driver = self.init_driver(headless)
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(data_dir, exist_ok=True)

    def init_driver(self, headless):
        options = uc.ChromeOptions()
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
            'all_previous_investments': []  # This is correctly defined here
        }

        # Extract investment stats from line-separated-row sections
        for row in soup.select('.line-separated-row.row'):
            # Get the label from the first column (col-xs-5)
            label_elem = row.select_one('.col-xs-5 .lh-solid')
            
            # Get the value from the second column (col-xs-7)
            value_elem = row.select_one('.col-xs-7 .lh-solid')
            
            if label_elem and value_elem:
                label = label_elem.text.strip(':')
                value = value_elem.text.strip()
                
                if 'Current Investing Position' in label:
                    # Extract just the company name from the value
                    profile['current_company'] = value.split(' at ')[-1] if ' at ' in value else value
                elif 'Investment Range' in label:
                    profile['investment_range'] = value
                elif 'Sweet Spot' in label:
                    profile['sweet_spot'] = value
                elif 'Current Fund Size' in label:
                    profile['current_fund_size'] = value
                elif 'Investments On Record' in label:
                    profile['investments_on_record'] = value 

        # Name Extraction
        name_tag = soup.select_one('.identity-block h1')
        if name_tag:
            profile['name'] = name_tag.get_text(strip=True).split('(')[0].strip()
    
        # Current Company Extraction - Updated Logic
        # Current Company Extraction - Fixed Logic
        current_company_span = soup.find('span', class_='section-label lh-solid', string='Current Investing Position')
        if current_company_span:
            parent_div = current_company_span.parent.parent  # Navigate to the row div
            company_div = parent_div.find('div', class_='col-xs-7')
            if company_div:
                company_link = company_div.find('a')
                if company_link:
                    profile['current_company'] = company_link.get_text(strip=True)
                else:
                    company_text = company_div.get_text(strip=True)
                    profile['current_company'] = company_text.split(' at ')[-1] if ' at ' in company_text else company_text        
        # Experience Section
        for exp in soup.select('.line-separated-row.flex.justify-between'):
            parts = exp.get_text(separator='|', strip=True).split('|')
            if len(parts) >= 3:
                profile['experience'].append({
                    'role': parts[0],
                    'company': parts[1],
                    'duration': parts[-1]
                })
    
        # Sector Rankings
        profile['sectors'] = [
            a.get_text(strip=True) 
            for section in soup.select('.sn-margin-top-30.relative') 
            if 'Sector & Stage Rankings' in section.text
            for a in section.select('a.vc-list-chip')
        ]
        
        profile['sector_rankings'] = [
            a.text.strip() 
            for section in soup.select('div.sn-margin-top-30.relative') 
            if 'Sector & Stage Rankings' in section.text
            for a in section.select('a.vc-list-chip')
        ]
    
        # Social Links
        # social_map = {
        #     'fa-linkedin': 'linkedin',
        #     'fa-twitter': 'twitter',
        #     'fa-angellist': 'angellist',
        #     'fa-globe': 'website'
        # }
        # profile['social_links'] = {
        #     social_map[icon['class'][1]]: link['href']
        #     for link in soup.select('.iconlink')
        #     if (icon := link.select_one('i')) 
        #     and len(icon.get('class', [])) > 1
        #     and icon['class'][1] in social_map
        # }
        social_links = {}
        links_container = soup.select_one('.sn-linkset')
        if links_container:
            for link in links_container.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com' in href:
                    social_links['linkedin'] = href
                elif 'twitter.com' in href:
                    social_links['twitter'] = href
                elif 'angel.co' in href:
                    social_links['angellist'] = href
                elif 'crunchbase.com' in href:
                    social_links['crunchbase'] = href
                elif 'homebrew.co' in href:  # Example for website
                    social_links['website'] = href

        profile['social_links'] = social_links
        # Network Memberships
        for network in soup.select('.mt2'):
            profile['network_memberships'].append({
                'network_name': network.select_one('.f6').text.strip(),
                'connection_count': ''.join(filter(str.isdigit, 
                    network.select_one('.f7').text))
            })
        # Education Section - Updated Implementation
        education = []
        for network in soup.select('.mt2'):
            network_name = network.select_one('.f6').text.strip()
            if 'university' in network_name.lower() or 'school' in network_name.lower():
                education.append({
                    'school': network_name,
                    'degree': 'Not specified',  # Can be enhanced if degree info is available
                    'year': 'Not specified'
                })
        profile['education'] = education

        investment_rows = soup.select('tbody.past-investments-table-body tr')
    
        for row in investment_rows:
            if 'coinvestors-row' not in row.get('class', []):
                investment = {}
                company = row.select_one('td.with-coinvestors div.round-padding')
                if company:
                    investment['company'] = company.text.strip()
                    
                stages = row.select('td.with-coinvestors div.round-padding')
                if stages and len(stages) > 1:
                    try:
                        stage_info = stages[1].text.strip().split('\u00b7')
                        if len(stage_info) >= 3:
                            investment['stage'] = stage_info[0].strip()
                            investment['date'] = stage_info[1].strip()
                            investment['round_size'] = stage_info[2].strip()
                    except IndexError:
                        pass
                
                # Current implementation (problematic):
                total_raised = row.select_one('td.with-coinvestors div.round-padding:last-child')
                
                # Proposed fix:
                total_raised = row.select_one('td.with-coinvestors:nth-child(3) div.round-padding')
                if total_raised:
                    investment['total_raised'] = total_raised.text.strip()
                    
                if investment:
                    profile['all_previous_investments'].append(investment)
        
        # Remove this problematic line:
        # profile_data['all_previous_investments'] = all_previous_investments
        
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
        try:
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
                
                # Rest of the button handling code remains the same
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
            # Add print statement here
            print('\nSuccessfully scraped profile:')
            pprint.pprint(profile)
            self.logger.info(f'Successfully scraped: {profile_url}')

        except Exception as e:
            self.logger.error(f'Failed to scrape {profile_url}: {str(e)}', exc_info=True)
            self.save_error(profile_url, str(e))

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,  # Change from INFO to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join('scraper.log')),
            logging.StreamHandler()
        ]
    )
    
    scraper = ProfileScraper(
        data_dir=os.getcwd(),
        headless=False
    )
    
    try:
        scraper.scrape_profile('https://signal.nfx.com/investors/satya-patel')
        scraper.save_profiles()
    except Exception as e:
        scraper.logger.error(f'Fatal error: {str(e)}')
    finally:
        scraper.driver.quit()