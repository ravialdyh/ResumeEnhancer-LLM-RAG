import asyncio
import random
import pytz
from playwright.async_api import async_playwright, BrowserContext, Page
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

# Constants from the original repository (adapted)
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
        delete navigator.__proto__.webdriver;
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

        const originalWorker = window.Worker;
        window.Worker = new Proxy(originalWorker, {
            construct(target, args) {
                const worker = new target(...args);
                const handleMessage = (event) => {
                    if (event.data === 'spoofHardwareConcurrency') {
                        worker.postMessage(navigator.hardwareConcurrency);
                    }
                };
                worker.addEventListener('message', handleMessage);
                return worker;
            }
        });
    })();
'''

def generate_device_specs() -> tuple:
    """Generate random RAM and hardware concurrency for fingerprint spoofing."""
    random_ram = random.choice([1, 2, 4, 8, 16, 32, 64])
    max_hw_concurrency = random_ram * 2 if random_ram < 64 else 64
    random_hw_concurrency = random.choice([1, 2, 4, max_hw_concurrency])
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
        print(f"Error performing {action} on {xpath}: {e}")
        return None

def parse_linkedin_url(url: str) -> str:
    """Parse the URL and reconstruct as public /jobs/view/{jobId} if currentJobId is present."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    job_id = query_params.get('currentJobId', [None])[0]
    if job_id:
        print(f"Detected currentJobId={job_id}; redirecting to public view URL.")
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return url  # Use as-is if no currentJobId

async def scrape_job_description(
    url: str,
    headless: bool = True,
    proxy: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Scrape the job description from a given LinkedIn job URL using Playwright.
    
    Args:
        url (str): The LinkedIn job URL (handles formats like /collections/recommended/?currentJobId=... or /jobs/view/...).
        headless (bool): Run browser in headless mode (default: True).
        proxy (Optional[Dict[str, str]]): Proxy settings {'server': 'http://ip:port', 'username': 'user', 'password': 'pass'} (optional).
    
    Returns:
        Optional[str]: The extracted job description, or None if failed.
    """
    # Parse and normalize URL to public view format
    normalized_url = parse_linkedin_url(url)
    
    async with async_playwright() as playwright:
        ram, hw_concurrency = generate_device_specs()
        spoof_script = SPOOF_FINGERPRINT_SCRIPT % (ram, hw_concurrency)
        
        browser = await playwright.firefox.launch(
            headless=headless,
            args=['--start-maximized', '--foreground', '--disable-backgrounding-occluded-windows'],
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
        
        try:
            await page.goto(normalized_url, wait_until='load', timeout=60000)
            print(f"Navigated to {normalized_url}")
            
            # Wait for description to appear
            await page.wait_for_selector(BODY_INFO_XPATH, timeout=30000)
            
            # Optional: Click "Show more" only if visible (short timeout, no error raise)
            show_more_locator = page.locator(SHOW_MORE_XPATH)
            if await show_more_locator.is_visible(timeout=2000):
                await base_action(page, SHOW_MORE_XPATH, 'click', timeout=5000)
            else:
                print("'Show more' button not visible; proceeding with extraction.")
            
            # Extract job description
            description = await base_action(page, BODY_INFO_XPATH, 'text_content', raise_error=True, timeout=15000)
            
            if description:
                # Clean up the description (remove extra newlines/whitespace)
                description = ' '.join(description.strip().split())
                print("Job description extracted successfully.")
                return description
            else:
                print("Failed to extract job description.")
                return None
        except Exception as e:
            print(f"Error scraping {normalized_url}: {e}")
            return None
        finally:
            await browser.close()

# Example usage
if __name__ == "__main__":
    job_url = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4079942516"
    
    # Optional proxy example (fetch from DB or hardcode; remove if not needed)
    # proxy = {'server': 'http://your_proxy_ip:port', 'username': 'user', 'password': 'pass'}
    proxy = None
    
    result = asyncio.run(scrape_job_description(job_url, headless=True, proxy=proxy))
    if result:
        print("\nJob Description:\n", result)
    else:
        print("No description found.")