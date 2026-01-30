"""
Job search scraper for LinkedIn.

Searches for jobs on LinkedIn and extracts job URLs.
"""
import asyncio
import logging
from typing import Optional, List
from urllib.parse import urlencode
from playwright.async_api import Page

from ..callbacks import ProgressCallback, SilentCallback
from .base import BaseScraper

logger = logging.getLogger(__name__)


class JobSearchScraper(BaseScraper):
    """
    Scraper for LinkedIn job search results.
    
    Example:
        async with BrowserManager() as browser:
            scraper = JobSearchScraper(browser.page)
            job_urls = await scraper.search(
                keywords="software engineer",
                location="San Francisco",
                limit=10
            )
    """
    
    def __init__(self, page: Page, callback: Optional[ProgressCallback] = None):
        """
        Initialize job search scraper.
        
        Args:
            page: Playwright page object
            callback: Optional progress callback
        """
        super().__init__(page, callback or SilentCallback())
    
    async def search(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25,
        search_url: Optional[str] = None,
        max_pages: int = 5
    ) -> List[str]:
        """
        Search for jobs on LinkedIn.

        Args:
            keywords: Job search keywords (e.g., "software engineer")
            location: Job location (e.g., "San Francisco, CA")
            limit: Maximum number of job URLs to return
            search_url: Optional direct LinkedIn job search URL to use instead of building one
            max_pages: Maximum number of pages to scrape (default: 5)

        Returns:
            List of job posting URLs
        """
        if search_url:
            logger.info(f"Starting job search with provided URL: {search_url}")
            await self.callback.on_start("JobSearch", search_url)
        else:
            logger.info(f"Starting job search: keywords='{keywords}', location='{location}'")
            search_url = self._build_search_url(keywords, location)
            await self.callback.on_start("JobSearch", search_url)
        
        await self.navigate_and_wait(search_url)
        await self.callback.on_progress("Navigated to search results", 10)

        # Collect jobs from multiple pages using URL-based pagination
        all_job_urls = []
        page_num = 1

        while len(all_job_urls) < limit and page_num <= max_pages:
            logger.info(f"Scraping page {page_num}")

            if page_num > 1:
                await self.callback.on_progress(f"Navigated to page {page_num}", 10 + (page_num - 1) * 20)

            # Construct URL for current page (25 jobs per page)
            url = self._construct_page_url(search_url, page_num)
            await self.navigate_and_wait(url)

            # Wait for job listings to appear
            try:
                await self.page.wait_for_selector('a[href*="/jobs/view/"], li[data-occludable-job-id]', timeout=10000)
            except:
                logger.warning(f"No job listings found on page {page_num} initially, continuing...")

            await self.wait_and_focus(2)

            # Scroll and click show more buttons to load all jobs on current page
            await self._load_all_jobs_on_page()

            await self.callback.on_progress(f"Loaded jobs on page {page_num}", 20 + (page_num - 1) * 20)

            # Extract job URLs from current page
            page_job_urls = await self._extract_job_urls_from_page(min(limit - len(all_job_urls), 50))  # Extract up to limit remaining or 50 per page
            all_job_urls.extend(page_job_urls)

            logger.info(f"Page {page_num}: found {len(page_job_urls)} jobs (total: {len(all_job_urls)})")

            if len(all_job_urls) >= limit:
                break

            page_num += 1
            await asyncio.sleep(2)  # Wait for page to load

        await self.callback.on_progress(f"Found {len(all_job_urls)} job URLs total", 90)

        # Remove duplicates while preserving order
        seen_urls = set()
        unique_job_urls = []
        for url in all_job_urls:
            if url not in seen_urls:
                unique_job_urls.append(url)
                seen_urls.add(url)

        if len(unique_job_urls) != len(all_job_urls):
            logger.info(f"Removed {len(all_job_urls) - len(unique_job_urls)} duplicate URLs")

        final_urls = unique_job_urls[:limit]  # Ensure we don't exceed limit

        await self.callback.on_progress("Search complete", 100)
        await self.callback.on_complete("JobSearch", final_urls)

        pages_scraped = min(page_num, max_pages)
        logger.info(f"Job search complete: found {len(final_urls)} unique jobs across {pages_scraped} pages")
        print(f"📊 Pagination Summary: {pages_scraped} pages scraped, {len(final_urls)} jobs collected")
        return final_urls
    
    def _build_search_url(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None
    ) -> str:
        """Build LinkedIn job search URL with parameters."""
        base_url = "https://www.linkedin.com/jobs/search/"

        params = {}
        if keywords:
            params['keywords'] = keywords
        if location:
            params['location'] = location

        if params:
            return f"{base_url}?{urlencode(params)}"
        return base_url

    def _construct_page_url(self, base_url: str, page_num: int) -> str:
        """Construct URL for a specific page using LinkedIn's pagination."""
        if page_num == 1:
            # Page 1 doesn't need a start parameter
            return base_url

        # LinkedIn jobs are paginated with 25 jobs per page
        # Page 1: no start parameter (start=0 implicitly)
        # Page 2: start=25
        # Page 3: start=50, etc.
        start_job = (page_num - 1) * 25

        if '?' in base_url:
            # URL already has parameters
            return f"{base_url}&start={start_job}"
        else:
            # URL has no parameters
            return f"{base_url}?start={start_job}"
    
    async def _load_all_jobs_on_page(self) -> None:
        """
        Scroll to bottom and click "Show more" buttons to load all jobs on current page.
        """
        # Scroll much more aggressively to load ALL jobs
        await self.scroll_page_to_bottom(pause_time=2.0, max_scrolls=15)

        # Try clicking "Show more" or "See more jobs" buttons repeatedly
        try:
            # Try multiple rounds of clicking show more buttons
            for round_idx in range(5):  # Up to 5 rounds
                show_more_buttons = await self.page.locator('button:has-text("Show more"), button:has-text("See more jobs"), button:has-text("Load more jobs"), button[aria-label*="more"]').all()
                if not show_more_buttons:
                    break

                clicked_count = 0
                for button in show_more_buttons[:3]:  # Up to 3 buttons per round
                    try:
                        await button.click(timeout=3000)
                        clicked_count += 1
                        await asyncio.sleep(3)  # Wait longer for more content to load
                        # Additional scrolling after each click
                        await self.scroll_page_to_bottom(pause_time=1.5, max_scrolls=3)
                        await asyncio.sleep(2)
                    except:
                        continue

                if clicked_count == 0:
                    break  # No more buttons to click

                # Extra scrolling to ensure all jobs load
                await self.scroll_page_to_bottom(pause_time=2.0, max_scrolls=8)

                logger.debug(f"Round {round_idx + 1}: Clicked {clicked_count} show more buttons")

        except Exception as e:
            logger.debug(f"Error during show more button clicking: {e}")

    async def _click_next_button(self) -> bool:
        """
        Click the "Next" button to go to the next page of results.

        Returns:
            True if successfully clicked Next button, False if no Next button found
        """
        try:
            # Use the specific XPath provided by the user
            next_button_xpath = '/html/body/div[1]/div[2]/div[2]/div[2]/main/div/div/div[1]/div/div[28]/button[2]/span'

            # Check if Next button exists and is not disabled
            next_button = self.page.locator(f'xpath={next_button_xpath}')
            if await next_button.is_visible() and await next_button.is_enabled():
                await next_button.click()
                logger.debug("Clicked Next button successfully")
                return True
            else:
                logger.debug("Next button not visible or disabled")
                return False

        except Exception as e:
            logger.debug(f"Error clicking Next button: {e}")
            return False

    async def _extract_job_urls_from_page(self, limit: int) -> List[str]:
        """
        Extract job URLs from current page.

        Args:
            limit: Maximum number of URLs to extract from this page

        Returns:
            List of job posting URLs from this page
        """
        job_urls = []

        try:
            # Try multiple selectors to find job links
            # LinkedIn uses different structures: direct links, job cards, etc.
            job_links = []

            # Method 1: Direct job links
            links1 = await self.page.locator('a[href*="/jobs/view/"]').all()
            job_links.extend(links1)

            # Method 2: Job cards with data attributes
            try:
                job_cards = await self.page.locator('li[data-occludable-job-id], div[data-job-id]').all()
                for card in job_cards:
                    # Find link within the card
                    link_in_card = await card.locator('a[href*="/jobs/view/"]').all()
                    job_links.extend(link_in_card)
            except:
                pass

            # Remove duplicates by converting to set of locators (not perfect, but helps)
            # We'll deduplicate by URL later

            seen_urls = set()
            for link in job_links:
                if len(job_urls) >= limit:
                    break

                try:
                    href = await link.get_attribute('href')
                    if href and '/jobs/view/' in href:
                        # Skip apply URLs
                        if '/apply/' in href:
                            continue

                        # Clean URL (remove query params and /apply/)
                        clean_url = href.split('?')[0] if '?' in href else href
                        clean_url = clean_url.replace('/apply', '')

                        # Ensure full URL
                        if not clean_url.startswith('http'):
                            clean_url = f"https://www.linkedin.com{clean_url}"

                        # Extract just the base job URL (remove any trailing paths)
                        if '/jobs/view/' in clean_url:
                            # Get the job ID part
                            parts = clean_url.split('/jobs/view/')
                            if len(parts) > 1:
                                job_id = parts[1].split('/')[0]
                                clean_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

                        # Avoid duplicates within this page
                        if clean_url not in seen_urls:
                            job_urls.append(clean_url)
                            seen_urls.add(clean_url)
                except Exception as e:
                    logger.debug(f"Error extracting job URL: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error extracting job URLs from page: {e}")

        return job_urls
