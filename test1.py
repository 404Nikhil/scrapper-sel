from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument("--headless") 
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--log-level=3")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def get_relevant_pages(site_url):
    driver.get(site_url)
    time.sleep(3)  # Allow page to load
    
    links = driver.find_elements(By.TAG_NAME, "a")
    relevant_links = []
    for link in links:
        href = link.get_attribute("href")
        if href and any(keyword in href.lower() for keyword in ["faq", "contact", "support", "help"]):
            relevant_links.append(href)
    
    return list(set(relevant_links))[:10] 

def extract_faqs():
    try:
        faqs = driver.find_elements(By.XPATH, "//h2[contains(text(), 'FAQ')]/following-sibling::ul/li")
        return [faq.text for faq in faqs if faq.text.strip()]
    except:
        return []

def extract_contact_info():
    try:
        contacts = driver.find_elements(By.XPATH, "//*[contains(text(), 'Contact') or contains(text(), 'Email') or contains(text(), 'Phone')]")
        return [contact.text for contact in contacts if contact.text.strip()]
    except:
        return []

def scrape_page(url):
    driver.get(url)
    time.sleep(3) 
    
    faqs = extract_faqs()
    contacts = extract_contact_info()
    
    return {
        "url": url,
        "faqs": faqs,
        "contacts": contacts
    }

def scrape_site(site_url):
    scraped_data = []
    relevant_pages = get_relevant_pages(site_url)
    
    for url in relevant_pages:
        data = scrape_page(url)
        scraped_data.append(data)
    
    driver.quit()
    
    with open("scraped_data.txt", "w", encoding="utf-8") as f:
        for entry in scraped_data:
            f.write(f"URL: {entry['url']}\n")
            f.write("FAQs:\n" + "\n".join(entry['faqs']) + "\n" if entry['faqs'] else "No FAQs found\n")
            f.write("Contacts:\n" + "\n".join(entry['contacts']) + "\n" if entry['contacts'] else "No Contact Info found\n")
            f.write("-" * 50 + "\n")
    
    print("Scraping complete. Data saved to scraped_data.txt")

site_url = ""
scrape_site(site_url)