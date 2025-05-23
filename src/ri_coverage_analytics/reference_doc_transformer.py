import requests
from bs4 import BeautifulSoup
import time
import re
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

def transform(web_page_uri: str, local_file: str):
    """
    Download a web page, transform it to markdown format, and save it locally.
    
    Args:
        web_page_uri (str): URL of the web page to download
        local_file (str): Path to save the markdown file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # For dynamic pages, use Selenium to render the page
        print(f"Downloading and rendering page: {web_page_uri}")
        
        # Configure Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Load the page and wait for it to render
        driver.get(web_page_uri)
        time.sleep(5)  # Wait for dynamic content to load
        
        # Get the page source after JavaScript execution
        page_source = driver.page_source
        driver.quit()
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Convert to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # Don't wrap text
        
        markdown_content = h.handle(str(soup))
        
        # Clean up the markdown
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)  # Remove excessive newlines
        
        # Save to file
        output_path = Path(local_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Successfully saved markdown to: {local_file}")
        return True
        
    except Exception as e:
        print(f"Error transforming document: {str(e)}")
        return False
