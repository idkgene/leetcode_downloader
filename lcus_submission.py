import os
import json
import time
import datetime
import sys
import getpass
import random
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Global Constants
TIMESTAMP = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
LEETCODE_URL = 'https://leetcode.com'
BATCH_SIZE = 20  # Number of submissions to fetch per request
MAX_WORKERS = 4  # Maximum number of parallel processing threads

# Mapping of LeetCode language identifiers to file extensions
LANG_EXTENSIONS = {
    'cpp': 'cpp', 'java': 'java', 'python': 'py', 'python3': 'py',
    'c': 'c', 'csharp': 'cs', 'javascript': 'js', 'ruby': 'rb',
    'swift': 'swift', 'golang': 'go', 'scala': 'scala', 'kotlin': 'kt',
    'rust': 'rs', 'mysql': 'sql', 'bash': 'sh'
}

def setup_logger():
    """
    Configure and initialize the logging system with both file and console outputs.
    
    The logger is configured with two handlers:
    1. File Handler: Detailed DEBUG level logs with timestamp and component info
    2. Console Handler: Concise INFO level logs with minimal timestamp
    
    Returns:
        logging.Logger: Configured logger instance
    """
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters for different output destinations
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure file handler for detailed logging
    file_handler = logging.FileHandler(
        log_dir / f'leetcode_scraper_{TIMESTAMP}.log',
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Configure console handler for user-friendly output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Setup root logger with both handlers
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

@dataclass
class Submission:
    """
    Data class representing a LeetCode submission.
    
    Attributes:
        title_slug (str): Problem identifier in URL-friendly format
        lang (str): Programming language of the submission
        timestamp (int): Unix timestamp of the submission
        status (str): Submission status (e.g., "Accepted", "Wrong Answer")
        code (str): Source code of the submission
    """
    title_slug: str
    lang: str
    timestamp: int
    status: str
    code: str

class LeetCodeScraper:
    """
    Main scraper class for downloading and organizing LeetCode submissions.
    
    This class handles:
    - User authentication
    - Chrome WebDriver setup and optimization
    - Parallel submission downloads
    - File organization and storage
    
    The scraper creates two main directories:
    1. lcus_[username]: Contains all submissions organized by problem
    2. Accepted: Contains only the accepted solutions
    """
    
    def __init__(self):
        """
        Initialize the scraper with user credentials and basic setup.
        
        Sets up logging, prompts for credentials, and initializes storage directories.
        Chrome WebDriver initialization is deferred until login.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.username = input('Username: ')
        self.password = getpass.getpass()
        self.driver = None
        self.wait = None
        self.accepted_slugs: Set[str] = set()
        self._setup_directories()
        
    def _setup_directories(self) -> None:
        """
        Create necessary directories for storing submissions and accepted solutions.
        
        Creates:
            - Base directory: lcus_[username]
            - Accepted solutions directory: Accepted
        """
        self.logger.debug("Setting up directories")
        self.base_dir = Path(f'lcus_{self.username}')
        self.accepted_dir = Path('Accepted')
        self.base_dir.mkdir(exist_ok=True)
        self.accepted_dir.mkdir(exist_ok=True)

    def _setup_driver(self) -> webdriver.Chrome:
        """
        Configure and initialize Chrome WebDriver with optimized settings.
        
        Configures Chrome for:
        - Maximum performance and stability
        - Automation detection avoidance
        - Resource usage optimization
        - Security and notification handling
        
        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance
        
        Raises:
            Exception: If driver initialization fails
        """
        self.logger.info("Initializing Chrome driver")
        options = webdriver.ChromeOptions()
        
        performance_options = [
            '--window-size=1920,1080',
            '--start-maximized',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer'
        ]
        
        security_options = [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--disable-extensions',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-logging',
            '--log-level=3'
        ]
        
        for opt in performance_options + security_options:
            options.add_argument(opt)

        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(driver, 20)
            return driver
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise

    def login(self) -> None:
        """
        Handle LeetCode login process with retry mechanism.
        
        Features:
        - Multiple retry attempts
        - Cloudflare verification handling
        - Robust error handling
        - Screenshot on failure
        
        Raises:
            Exception: If login fails after maximum retries
        """
        MAX_RETRIES = 3
        self.logger.info("Starting login process")
        
        for attempt in range(MAX_RETRIES):
            try:
                if not self.driver:
                    self.driver = self._setup_driver()
                
                self.logger.debug("Navigating to login page")
                self.driver.get(f'{LEETCODE_URL}/accounts/login/')
                
                self.logger.debug("Waiting for login form")
                username_field = self.wait.until(EC.presence_of_element_located((By.ID, 'id_login')))
                
                username_field.send_keys(self.username)
                time.sleep(random.uniform(0.5, 1))
                
                password_field = self.driver.find_element(By.ID, 'id_password')
                password_field.send_keys(self.password)
                
                self.logger.info("\nPlease complete the Cloudflare verification...")
                input("Press Enter after verification when you see the LeetCode homepage...")
                
                if self.wait.until(EC.url_changes(f'{LEETCODE_URL}/accounts/login/')):
                    self.logger.info("Login successful!")
                    return
                
            except Exception as e:
                self.logger.error(f"Login attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    self.driver.save_screenshot(f'error_{TIMESTAMP}.png')
                    raise
                time.sleep(2)
                
                # Restart driver on retry
                if self.driver:
                    self.driver.quit()
                    self.driver = None

    def _process_submission(self, submission: dict) -> None:
        """
        Process and save a single submission.
        
        This method:
        1. Creates a Submission object from API response
        2. Saves full submission data as JSON
        3. For accepted solutions, saves code file separately
        
        Args:
            submission (dict): Raw submission data from LeetCode API
        
        Note:
            Submissions are saved in two locations:
            1. [base_dir]/[problem_slug]/[timestamp].json - Full submission data
            2. Accepted/[problem_slug].[extension] - Latest accepted solution
        """
        try:
            sub = Submission(
                title_slug=submission['title_slug'],
                lang=submission['lang'],
                timestamp=submission['timestamp'],
                status=submission['status_display'],
                code=submission['code']
            )
            
            folder_path = self.base_dir / sub.title_slug
            json_path = folder_path / f'{sub.timestamp}.json'
            
            if json_path.exists():
                self.logger.debug(f"Skipping existing submission: {sub.title_slug}")
                return

            folder_path.mkdir(exist_ok=True)
            with json_path.open('w', encoding='utf-8') as f:
                json.dump(submission, f, indent=4, ensure_ascii=False)
            
            if sub.status == 'Accepted' and sub.title_slug not in self.accepted_slugs:
                self.accepted_slugs.add(sub.title_slug)
                extension = LANG_EXTENSIONS.get(sub.lang, sub.lang)
                accepted_path = self.accepted_dir / f'{sub.title_slug}.{extension}'
                with accepted_path.open('w', encoding='utf-8') as f:
                    f.write(sub.code)
                self.logger.info(f"Saved accepted solution: {sub.title_slug}")
                
        except Exception as e:
            self.logger.error(f"Error processing submission {submission.get('title_slug', 'unknown')}: {e}")

    def fetch_submissions(self) -> None:
        """
        Fetch all submissions using LeetCode's API with parallel processing.
        
        Features:
        - Batch processing with configurable size
        - Parallel processing using ThreadPoolExecutor
        - Automatic pagination
        - Robust error handling with retries
        """
        self.logger.info("Starting submission fetch")
        offset = 0
        
        while True:
            url = f'{LEETCODE_URL}/api/submissions/?offset={offset}&limit={BATCH_SIZE}&lastkey='
            try:
                self.driver.get(url)
                time.sleep(2)
                
                body = self.driver.find_element(by=By.TAG_NAME, value='body').text
                result = json.loads(body)
                
                submissions = result.get('submissions_dump', [])
                if not submissions:
                    self.logger.info("No more submissions to fetch")
                    break

                self.logger.info(f"Processing {len(submissions)} submissions from offset {offset}")
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    executor.map(self._process_submission, submissions)

                offset += BATCH_SIZE
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON at offset {offset}: {e}")
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Error fetching submissions at offset {offset}: {e}")
                time.sleep(5)

    def run(self) -> None:
        """
        Execute the main scraping workflow.
        
        Workflow:
        1. Login to LeetCode
        2. Fetch all submissions
        3. Clean up resources
        
        This method handles the high-level orchestration and ensures
        proper cleanup of resources even in case of errors.
        """
        try:
            self.login()
            self.fetch_submissions()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            raise
        finally:
            if self.driver:
                self.logger.info("Closing Chrome driver")
                self.driver.quit()

if __name__ == '__main__':
    # Initialize logging and start the scraping process
    logger = setup_logger()
    try:
        logger.info("Starting LeetCode Submission Scraper")
        scraper = LeetCodeScraper()
        scraper.run()
        logger.info("Scraping completed successfully")
    except Exception as e:
        logger.error(f"Program terminated with error: {e}")
        sys.exit(1)
