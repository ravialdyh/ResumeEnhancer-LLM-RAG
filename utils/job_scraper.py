import asyncio
from playwright.async_api import async_playwright
import trafilatura
import json
from bs4 import BeautifulSoup

async def scrape_job_description(url: str) -> str:
    """
    Asynchronously scrapes the job description from a given URL.

    This function will first attempt to find structured data (JSON-LD) for the job posting.
    If not found, it will fall back to extracting the main text content of the page.

    Args:
        url (str): The URL of the job posting.

    Returns:
        str: The extracted job description text, or an empty string if it fails.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            html_content = await page.content()
            await browser.close()

            # 1. Prioritize Schema.org/JobPosting JSON-LD
            soup = BeautifulSoup(html_content, 'html.parser')
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script:
                json_data = json.loads(json_ld_script.string)
                if json_data.get('@type') == 'JobPosting' and 'description' in json_data:
                    # Extract description from structured data for higher accuracy
                    job_description_html = json_data['description']
                    # Convert HTML in description to plain text
                    return BeautifulSoup(job_description_html, 'html.parser').get_text(separator='\n').strip()

            # 2. Fallback to trafilatura for main content extraction
            return trafilatura.extract(html_content, include_comments=False, include_tables=False)

    except Exception as e:
        print(f"An error occurred while scraping the URL: {e}")
        return ""