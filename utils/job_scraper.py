# utils/job_scraper.py
import asyncio
import random
import pytz
from playwright.async_api import async_playwright, BrowserContext, Page
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs
from loguru import logger

# --- Constants and helpers from the successful script ---
SHOW_MORE_XPATH = '(//button[contains(text(), "Show more")])[1]'
BODY_INFO_XPATH = '//div[contains(@class, "show-more-less-html__markup")]'
FIREFOX_SETTINGS = {
    "pdfjs.disabled": False,
    "browser.taskbar.lists.enabled": True,
    "browser.taskbar.lists.frequent.enabled": True,
    "browser.taskbar.lists.recent.enabled": True,
    "browser.taskbar.lists.tasks.enabled": True,
    "browser.taskbar.lists.maxListItemCount": 10,
}
SPOOF_FINGERPRINT_SCRIPT = '''
    (() => {
        if (navigator.webdriver) {
            delete navigator.__proto__.webdriver;
        }
        Object.defineProperty(navigator, 'deviceMemory', {
            value: %d, configurable: true
        });

        const originalHardwareConcurrency = navigator.hardwareConcurrency;
        const originalPropertyDescriptor = Object.getOwnPropertyDescriptor(
            Navigator.prototype, 'hardwareConcurrency'
        );
        Object.defineProperty(Navigator.prototype, 'hardwareConcurrency', {
            get: function() {
                return %d;
            },
            enumerable: originalPropertyDescriptor.enumerable,
            configurable: originalPropertyDescriptor.configurable,
        });
    })();
'''

def generate_device_specs() -> tuple:
    """Generate random RAM and hardware concurrency for fingerprint spoofing."""
    random_ram = random.choice([2, 4, 8, 16, 32])
    max_hw_concurrency = random_ram * 2
    random_hw_concurrency = random.choice([2, 4, 8, 16, max_hw_concurrency])
    return (random_ram, random_hw_concurrency)

async def base_action(
    page: Page,
    xpath: str,
    action: str,
    timeout: int = 5000,
    raise_error: bool = False,
    **kwargs
) -> Optional[str]:
    """Helper to perform actions like click or text_content on XPath."""
    try:
        result = await getattr(page.locator(xpath), action)(timeout=timeout, **kwargs)
        return result
    except Exception as e:
        if raise_error:
            raise e
        logger.warning(f"Non-critical error performing {action} on {xpath}: {e}")
        return None

def parse_linkedin_url(url: str) -> str:
    """Parse the URL and reconstruct as public /jobs/view/{jobId} if currentJobId is present."""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        job_id = query_params.get('currentJobId', [None])[0]
        if job_id:
            logger.info(f"Detected currentJobId={job_id}; redirecting to public view URL.")
            return f"https://www.linkedin.com/jobs/view/{job_id}/"
    except Exception:
        logger.warning("Could not parse Job ID from URL, using original URL.")
    return url

async def scrape_job_description(
    url: str,
    headless: bool = True,
    proxy: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Scrape the job description from a given LinkedIn job URL using Playwright with anti-scraping measures.
    """
    normalized_url = parse_linkedin_url(url)
    logger.info(f"Starting to scrape URL: {normalized_url}")
    
    browser = None
    async with async_playwright() as playwright:
        ram, hw_concurrency = generate_device_specs()
        spoof_script = SPOOF_FINGERPRINT_SCRIPT % (ram, hw_concurrency)
        
        try:
            browser = await playwright.firefox.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--start-maximized',
                    '--foreground',
                    '--disable-backgrounding-occluded-windows'
                ],
                firefox_user_prefs=FIREFOX_SETTINGS
            )
            context: BrowserContext = await browser.new_context(
                timezone_id=random.choice(pytz.all_timezones),
                accept_downloads=True,
                is_mobile=False,
                has_touch=False,
                proxy=proxy
            )
            page: Page = await context.new_page()
            await page.bring_to_front()
            await page.add_init_script(spoof_script)
            
            # Increased navigation timeout for robustness
            await page.goto(normalized_url, wait_until='domcontentloaded', timeout=90000)
            logger.info(f"Navigated to {normalized_url}")
            
            await page.wait_for_selector(BODY_INFO_XPATH, timeout=30000)
            
            show_more_locator = page.locator(SHOW_MORE_XPATH)
            if await show_more_locator.is_visible(timeout=3000):
                await base_action(page, SHOW_MORE_XPATH, 'click', timeout=5000)
            else:
                logger.info("'Show more' button not visible or needed; proceeding with extraction.")
            
            description = await base_action(page, BODY_INFO_XPATH, 'text_content', raise_error=True, timeout=15000)
            
            if description:
                description = ' '.join(description.strip().split())
                logger.success("Job description extracted successfully.")
                return description
            else:
                logger.error("Failed to extract job description content.")
                return None
        except Exception as e:
            logger.error(f"A critical error occurred while scraping {normalized_url}: {e}")
            return None
        finally:
            if browser and browser.is_connected():
                await browser.close()
