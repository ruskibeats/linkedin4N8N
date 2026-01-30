"""
Job scraper for LinkedIn.

Extracts job posting information from LinkedIn job pages.
"""
import asyncio
import logging
from typing import Optional
from playwright.async_api import Page

from ..models.job import Job
from ..core.exceptions import ProfileNotFoundError
from ..callbacks import ProgressCallback, SilentCallback
from .base import BaseScraper

logger = logging.getLogger(__name__)


class JobScraper(BaseScraper):
    """
    Scraper for LinkedIn job postings.
    
    Example:
        async with BrowserManager() as browser:
            scraper = JobScraper(browser.page)
            job = await scraper.scrape("https://www.linkedin.com/jobs/view/123456/")
            print(job.to_json())
    """
    
    def __init__(self, page: Page, callback: Optional[ProgressCallback] = None):
        """
        Initialize job scraper.
        
        Args:
            page: Playwright page object
            callback: Optional progress callback
        """
        super().__init__(page, callback or SilentCallback())
    
    async def scrape(self, linkedin_url: str) -> Job:
        """
        Scrape a LinkedIn job posting.
        
        Args:
            linkedin_url: URL of the LinkedIn job posting
            
        Returns:
            Job object with scraped data
            
        Raises:
            ProfileNotFoundError: If job posting not found
        """
        logger.info(f"Starting job scraping: {linkedin_url}")
        await self.callback.on_start("Job", linkedin_url)
        
        # Navigate to job page
        await self.navigate_and_wait(linkedin_url)
        await self.callback.on_progress("Navigated to job page", 10)
        
        # Wait a bit for page to fully render
        await self.wait_and_focus(2.0)
        
        # Check if page exists
        await self.check_rate_limit()
        
        # Wait for main content to load
        try:
            await self.page.wait_for_selector('main', timeout=10000)
            # Wait for job details to appear
            await asyncio.sleep(1)
        except:
            logger.warning("Main content not found, continuing anyway")
        
        # Extract job details
        job_title = await self._get_job_title()
        await self.callback.on_progress(f"Got job title: {job_title}", 20)
        
        company = await self._get_company()
        await self.callback.on_progress("Got company name", 30)
        
        location = await self._get_location()
        await self.callback.on_progress("Got location", 40)
        
        posted_date = await self._get_posted_date()
        await self.callback.on_progress("Got posted date", 50)
        
        applicant_count = await self._get_applicant_count()
        await self.callback.on_progress("Got applicant count", 60)
        
        employment_type = await self._get_employment_type()
        await self.callback.on_progress("Got employment type", 65)
        
        salary = await self._get_salary()
        await self.callback.on_progress("Got salary", 70)
        
        job_description = await self._get_description()
        await self.callback.on_progress("Got job description", 80)
        
        company_url = await self._get_company_url()
        await self.callback.on_progress("Got company URL", 90)
        
        # Create job object
        job = Job(
            linkedin_url=linkedin_url,
            job_title=job_title,
            company=company,
            company_linkedin_url=company_url,
            location=location,
            posted_date=posted_date,
            applicant_count=applicant_count,
            employment_type=employment_type,
            salary=salary,
            job_description=job_description
        )
        
        await self.callback.on_progress("Scraping complete", 100)
        await self.callback.on_complete("Job", job)
        
        logger.info(f"Successfully scraped job: {job_title}")
        return job
    
    async def _get_job_title(self) -> Optional[str]:
        """Extract job title from page title."""
        try:
            # LinkedIn puts the job title in the page title format: "Job Title | Company | LinkedIn"
            page_title = await self.page.title()
            if page_title and '|' in page_title:
                # Split by | and get the first part (job title)
                parts = page_title.split('|')
                if len(parts) >= 2:
                    job_title = parts[0].strip()
                    if job_title and len(job_title) > 3:
                        return job_title
        except Exception as e:
            logger.debug(f"Error extracting job title: {e}")
        return None
    
    async def _get_company(self) -> Optional[str]:
        """Extract company name from company link."""
        try:
            # Try multiple selectors for company name
            selectors = [
                'a[href*="/company/"]',
                '.job-details-jobs-unified-top-card__company-name a',
                '.jobs-unified-top-card__company-name a',
                'a[data-test-id="job-poster-name"]'
            ]
            
            for selector in selectors:
                try:
                    company_links = await self.page.locator(selector).all()
                    for link in company_links[:10]:  # Limit to first 10
                        try:
                            text = await link.inner_text(timeout=2000)
                            text = text.strip()
                            # Skip empty or very short text (likely image-only links)
                            if text and len(text) > 1 and len(text) < 100 and not text.lower().startswith('logo'):
                                return text
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            logger.debug(f"Error extracting company: {e}")
        return None
    
    async def _get_company_url(self) -> Optional[str]:
        """Extract company LinkedIn URL."""
        try:
            company_link = self.page.locator('a[href*="/company/"]').first
            if await company_link.count() > 0:
                href = await company_link.get_attribute('href')
                if href:
                    if '?' in href:
                        href = href.split('?')[0]
                    if not href.startswith('http'):
                        href = f"https://www.linkedin.com{href}"
                    return href
        except:
            pass
        return None
    
    async def _get_location(self) -> Optional[str]:
        """Extract job location from job details panel."""
        try:
            # Look for location in main content spans
            main_content = self.page.locator('main').first
            if await main_content.count() > 0:
                text_elements = await main_content.locator('span').all()
                for elem in text_elements[:15]:  # Check first 15 spans
                    try:
                        text = await elem.inner_text(timeout=500)
                        if text and len(text) > 10 and len(text) < 150:
                            text = text.strip()
                            # Location patterns - must have city and country
                            if any(indicator in text for indicator in [', United Kingdom', ', UK', ', England', 'London,', 'Remote', ', United States', ', US', 'New York', 'San Francisco']):
                                # Make sure it's not a sentence
                                if text.count(',') >= 1 and not text.lower().startswith('find'):
                                    return text
                    except:
                        continue
        except:
            pass
        return None
    
    async def _get_posted_date(self) -> Optional[str]:
        """Extract posted date from job details."""
        try:
            # Search in main content for time patterns
            main_content = self.page.locator('main').first
            if await main_content.count() > 0:
                text_elements = await main_content.locator('span').all()
                for elem in text_elements[:20]:  # Check first 20 spans
                    try:
                        text = await elem.inner_text(timeout=500)
                        if text and len(text) < 30:
                            text = text.strip()
                            # Posted date patterns: "X days ago", "X hours ago", "X weeks ago"
                            if 'ago' in text.lower() and any(x in text.lower() for x in ['hour', 'day', 'week', 'month']):
                                # Make sure it's a proper time string
                                if text[0].isdigit() or text.lower().startswith('reposted'):
                                    return text
                    except:
                        continue
        except:
            pass
        return None
    
    async def _get_applicant_count(self) -> Optional[str]:
        """Extract applicant count from job details."""
        try:
            main_content = self.page.locator('main').first
            if await main_content.count() > 0:
                text_elements = await main_content.locator('span').all()
                for elem in text_elements[:20]:  # Check first 20 spans
                    try:
                        text = await elem.inner_text(timeout=500)
                        text = text.strip()
                        if text and len(text) < 60:
                            text_lower = text.lower()
                            # Applicant patterns: "Over X applicants", "X applicants", "Be among the first 25 applicants"
                            if 'applicant' in text_lower:
                                return text
                    except:
                        continue
        except:
            pass
        return None
    
    async def _get_employment_type(self) -> Optional[str]:
        """Extract employment type (Full-time, Contract, Part-time, etc.)."""
        try:
            main_content = self.page.locator('main').first
            if await main_content.count() > 0:
                text_elements = await main_content.locator('span').all()
                for elem in text_elements[:30]:
                    try:
                        text = await elem.inner_text(timeout=500)
                        text = text.strip()
                        # Employment type patterns
                        if text in ['Full-time', 'Part-time', 'Contract', 'Temporary', 'Internship', 'Volunteer']:
                            return text
                    except:
                        continue
        except:
            pass
        return None
    
    async def _get_salary(self) -> Optional[str]:
        """Extract salary information if posted."""
        try:
            main_content = self.page.locator('main').first
            if await main_content.count() > 0:
                text_elements = await main_content.locator('span, div').all()
                for elem in text_elements[:50]:
                    try:
                        text = await elem.inner_text(timeout=500)
                        text = text.strip()
                        if text and len(text) < 100:
                            # Salary patterns: contains currency symbols or salary keywords
                            if ('£' in text or '$' in text or '€' in text) and any(x in text for x in ['year', 'hour', 'month', 'k', 'K', '-']):
                                return text
                            # Also check for explicit salary mentions
                            if 'salary' in text.lower() and len(text) < 80 and any(c.isdigit() for c in text):
                                return text
                    except:
                        continue
        except:
            pass
        return None
    
    async def _get_description(self) -> Optional[str]:
        """Extract job description from 'About the job' section."""
        try:
            # Find "About the job" heading
            about_heading = self.page.locator('h2:has-text("About the job")').first
            if await about_heading.count() > 0:
                # Get parent's parent (go up two levels)
                parent_parent = about_heading.locator('xpath=../..')
                if await parent_parent.count() > 0:
                    description = await parent_parent.inner_text(timeout=5000)
                    if description and len(description.strip()) > 50:
                        # Remove "About the job" heading if included
                        desc = description.strip()
                        if desc.startswith('About the job'):
                            desc = desc[13:].strip()
                        return desc
        except Exception as e:
            logger.debug(f"Error extracting description: {e}")
        return None
