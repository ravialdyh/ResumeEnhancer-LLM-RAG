import asyncio
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from loguru import logger

async def scrape_job_description(url: str) -> str:
    """
    Asynchronously scrapes the job description from a given URL, with improved reliability for dynamic sites.
    
    This function will:
    1. Launch a browser and navigate to the URL.
    2. Wait for a specific, common selector for job descriptions to appear.
    3. Attempt to parse structured JSON-LD data first for accuracy.
    4. Fall back to a more robust text extraction from the main content area.
    
    Args:
        url (str): The URL of the job posting.
    Returns:
        str: The extracted job description text, or an empty string if it fails.
    """
    logger.info(f"Starting to scrape URL: {url}")
    
    # Selectors that commonly contain job descriptions on platforms like LinkedIn
    job_description_selectors = [
        'div.description__text',
        'div.jobs-description__content',
        'div.show-more-less-html__markup',
        'section.jobs-description',
        'article.job-description'
    ]
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Check for login/security walls before proceeding
                if "authwall" in page.url or "login" in page.url:
                    logger.warning(f"Redirected to a login/auth wall at {page.url}. Scraping will likely fail.")
                    await browser.close()
                    return "" # Return empty string as we can't scrape
                
                # Wait for any of the potential job description containers to be visible
                combined_selector = ", ".join(job_description_selectors)
                await page.wait_for_selector(combined_selector, state="visible", timeout=30000)
                logger.info("Job description container is visible.")

            except Exception as e:
                logger.error(f"Failed to load page or find selector for {url}: {e}")
                # Still try to get content in case the page loaded but selector timed out
            
            html_content = await page.content()
            await browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')

            # 1. Prioritize Schema.org/JobPosting JSON-LD for accuracy
            try:
                json_ld_script = soup.find('script', type='application/ld+json')
                if json_ld_script:
                    json_data = json.loads(json_ld_script.string)
                    if isinstance(json_data, list): # Handle cases where JSON-LD is a list
                        json_data = next((item for item in json_data if item.get('@type') == 'JobPosting'), None)
                    
                    if json_data and json_data.get('@type') == 'JobPosting' and 'description' in json_data:
                        logger.info("Found and extracted description from JSON-LD.")
                        job_description_html = json_data['description']
                        # Convert HTML in description to plain text
                        return BeautifulSoup(job_description_html, 'html.parser').get_text(separator='\n').strip()
            except Exception as e:
                logger.warning(f"Could not parse JSON-LD script: {e}")

            # 2. Fallback to extracting from the main content container
            main_content_area = soup.select_one(", ".join(job_description_selectors))
            if main_content_area:
                logger.info("Extracting text from primary content area.")
                return main_content_area.get_text(separator='\n').strip()
            
            logger.warning("Primary selectors failed. No job description found on the page.")
            return ""

    except Exception as e:
        logger.error(f"A critical error occurred while scraping {url}: {e}")
        return ""