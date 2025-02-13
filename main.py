import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urljoin
import csv
import time
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import queue
from threading import Lock

class WebScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.visited_urls = set()
        self.data = []
        self.data_lock = Lock()
        self.url_lock = Lock()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--disable-javascript')
        options.page_load_strategy = 'eager'
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20) 
        driver.implicitly_wait(5) 
        return driver

    def is_valid_url(self, url):
        """Check if URL is valid for scraping"""
        invalid_fragments = ['#carousel', '#skip', 'javascript:', 'mailto:']
        return not any(fragment in url for fragment in invalid_fragments)

    def scrape_page(self, url):
        """Scrape content from a single page with optimized timing"""
        if not self.is_valid_url(url):
            return []

        driver = None
        try:
            with self.url_lock:
                if url in self.visited_urls:
                    return []
                self.visited_urls.add(url)

            driver = self.setup_driver()
            self.logger.info(f"Scraping: {url}")
            
            for attempt in range(3):
                try:
                    driver.get(url)
                    break
                except TimeoutException:
                    if attempt == 2:
                        raise
                    driver.refresh()
                    time.sleep(1)

            try:
                main_content = driver.find_element(By.TAG_NAME, 'main').text
            except:
                try:
                    main_content = driver.find_element(By.CLASS_NAME, 'container').text
                except:
                    main_content = driver.find_element(By.TAG_NAME, 'body').text

            links = driver.find_elements(By.TAG_NAME, 'a')
            new_links = []
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and href.startswith(self.base_url) and self.is_valid_url(href):
                        new_links.append(href)
                except:
                    continue

            with self.data_lock:
                self.data.append({
                    'url': url,
                    'content': main_content
                })

            return list(set(new_links))

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return []
        finally:
            if driver:
                driver.quit()

    def scrape_site(self, max_pages=None, max_workers=3):
        """Scrape the site with controlled concurrency"""
        pages_to_visit = queue.Queue()
        pages_to_visit.put(self.base_url)
        pages_scraped = 0
        
        def worker():
            while True:
                try:
                    if max_pages and pages_scraped >= max_pages:
                        break
                        
                    try:
                        url = pages_to_visit.get(timeout=5)
                    except queue.Empty:
                        break

                    new_links = self.scrape_page(url)
                    time.sleep(1) 
                    
                    for link in new_links:
                        if link not in self.visited_urls:
                            pages_to_visit.put(link)
                            
                    pages_to_visit.task_done()
                    
                except Exception as e:
                    self.logger.error(f"Worker error: {str(e)}")
                    continue

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            workers = [executor.submit(worker) for _ in range(max_workers)]
            for future in workers:
                future.result()

    def save_to_txt(self, filename='scraped_data.txt'):
        with open(filename, 'w', encoding='utf-8') as file:
            for item in self.data:
                file.write(f"URL: {item['url']}\n")
                file.write("Content:\n")
                file.write(f"{item['content']}\n")
                file.write("-" * 80 + "\n")

if __name__ == "__main__":
    scraper = WebScraper("")
    scraper.scrape_site(max_pages=20, max_workers=3) 
    scraper.save_to_txt()