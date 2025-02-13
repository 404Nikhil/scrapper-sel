from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import os
import argparse
import sys
from urllib.parse import urlparse, urljoin
from collections import deque
from dotenv import load_dotenv

load_dotenv()

def get_chrome_paths():
    """Get OS-specific Chrome paths"""
    if sys.platform.startswith('win'):
        return {
            'chrome': os.environ.get("CHROME_BIN") or 
                     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            'driver': os.path.join(os.getcwd(), "chromedriver.exe")
        }
    elif sys.platform.startswith('linux'):
        return {
            'chrome': os.environ.get("CHROME_BIN") or 
                     "/usr/bin/chromium-browser",
            'driver': "/usr/bin/chromedriver"
        }
    else:
        raise OSError("Unsupported operating system")

def scrape_website(website):
    """Scrape website content using headless Chrome"""
    print("Setting up Chrome options...")
    options = Options()
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-software-rasterizer")

    paths = get_chrome_paths()
    
    if not os.path.exists(paths['chrome']):
        raise FileNotFoundError(f"Chrome not found at: {paths['chrome']}")
    options.binary_location = paths['chrome']

    print("Initializing WebDriver...")
    driver = None
    try:
        service = Service(
            executable_path=paths['driver'],
            service_args=["--verbose", "--log-path=chromedriver.log"]
        )
        
        if sys.platform.startswith('linux'):
            options.add_argument("--single-process")
        
        driver = webdriver.Chrome(service=service, options=options)
        print(f"Using Chrome {driver.capabilities['browserVersion']}")
        
        print("Navigating to website...")
        driver.get(website)
        return driver.page_source
        
    except Exception as e:
        print(f"Chrome initialization failed: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()

def extract_body_content(html_content):
    """Extract body content using BeautifulSoup"""
    soup = BeautifulSoup(html_content, "html.parser")
    return str(soup.body) if soup.body else "No body content found"

def clean_body_content(body_content):
    """Clean and format the body content"""
    soup = BeautifulSoup(body_content, "html.parser")
    cleaned = soup.get_text(separator='\n', strip=True)
    return '\n'.join(line for line in cleaned.splitlines() if line)

def main():
    """Main function to handle command-line arguments and crawling logic"""
    parser = argparse.ArgumentParser(description='Scrape website content.')
    parser.add_argument('--url', required=True, help='Website URL to scrape')
    parser.add_argument('--output', required=True, help='Output .txt file')
    parser.add_argument('--max-pages', type=int, default=5,
                       help='Maximum number of pages to scrape (default: 5)')
    args = parser.parse_args()

    visited = set()
    queue = deque([args.url])
    base_domain = urlparse(args.url).netloc

    with open(args.output, 'w', encoding='utf-8') as f:
        while queue and len(visited) < args.max_pages:
            current_url = queue.popleft()
            
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                print(f"Scraping: {current_url}")
                html = scrape_website(current_url)
                cleaned = clean_body_content(extract_body_content(html))
                
                f.write(f"=== URL: {current_url} ===\n{cleaned}\n\n")

                soup = BeautifulSoup(html, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(current_url, href).split('#')[0]
                    parsed_url = urlparse(absolute_url)
                    
                    if (parsed_url.netloc == base_domain 
                        and absolute_url not in visited
                        and absolute_url not in queue):
                        queue.append(absolute_url)

            except Exception as e:
                print(f"Error processing {current_url}: {str(e)}")

    print(f"Scraping complete. Results saved to {args.output}")

if __name__ == "__main__":
    main()