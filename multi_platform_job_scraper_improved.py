#!/usr/bin/env python3
"""
Multi-Platform Job Scraper - LinkedIn + JobServe (IMPROVED VERSION)

Enhanced with:
- Logging framework
- Retry logic
- Config validation
- Async JobServe scraping
- Centralized selectors
- Metrics tracking
- Progress bars

Configure via multi_platform_config.json
"""

import asyncio
import json
import logging
import sys
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

from linkedin_scraper import BrowserManager, JobSearchScraper, JobScraper, ConsoleCallback
from scraper_config import ScraperConfig, JOBSERVE_SELECTORS, SCRAPING_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScraperMetrics:
    """Track scraping metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.jobs_scraped = 0
        self.jobs_matched = 0
        self.webhook_successes = 0
        self.webhook_failures = 0
        self.linkedin_jobs = 0
        self.jobserve_jobs = 0
        self.errors = []
    
    def duration(self) -> float:
        return time.time() - self.start_time
    
    def to_dict(self) -> dict:
        return {
            'duration_seconds': round(self.duration(), 2),
            'jobs_scraped': self.jobs_scraped,
            'jobs_matched': self.jobs_matched,
            'webhook_successes': self.webhook_successes,
            'webhook_failures': self.webhook_failures,
            'linkedin_jobs': self.linkedin_jobs,
            'jobserve_jobs': self.jobserve_jobs,
            'success_rate': f"{(self.webhook_successes / max(self.jobs_matched, 1) * 100):.1f}%",
            'errors': self.errors[:10]  # Last 10 errors
        }
    
    def save_to_file(self, filepath: str = 'scraper_metrics.json'):
        """Save metrics to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Metrics saved to {filepath}")


def load_config(config_file: str = "multi_platform_config.json") -> ScraperConfig:
    """Load and validate configuration from JSON file."""
    if not Path(config_file).exists():
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        # Validate using Pydantic
        config = ScraperConfig(**data)
        logger.info(f"Configuration loaded and validated successfully")
        return config
        
    except Exception as e:
        logger.error(f"Invalid configuration: {e}")
        sys.exit(1)


def parse_posted_date(posted_date: str) -> Optional[int]:
    """Parse posted date string to days ago."""
    if not posted_date:
        return None
    
    posted_date = posted_date.lower()
    match = re.search(r'(\d+)', posted_date)
    if not match:
        return None
    
    num = int(match.group(1))
    
    if 'hour' in posted_date:
        return 0 if num < 24 else 1
    elif 'day' in posted_date:
        return num
    elif 'week' in posted_date:
        return num * 7
    elif 'month' in posted_date:
        return num * 30
    
    return None


def filter_job(job: dict, filters: dict) -> tuple[bool, str]:
    """Check if job matches filter criteria."""
    # Filter by posted date
    if filters.get('max_posted_days_ago'):
        days_ago = parse_posted_date(job.get('posted_date', ''))
        if days_ago is None or days_ago > filters['max_posted_days_ago']:
            return False, f"Posted {days_ago} days ago (max: {filters['max_posted_days_ago']})"
    
    # Filter by employment type
    if filters.get('employment_types'):
        job_type = job.get('employment_type') or job.get('job_type')
        if not job_type:
            return False, f"No employment type (need: {', '.join(filters['employment_types'])})"
        
        # Normalize job types
        job_type_normalized = job_type.lower()
        filter_types_normalized = [t.lower() for t in filters['employment_types']]
        
        if job_type_normalized not in filter_types_normalized:
            return False, f"Type '{job_type}' not in {filters['employment_types']}"
    
    # Filter by location
    if filters.get('locations'):
        job_location = job.get('location', '')
        if job_location:
            if not any(loc.lower() in job_location.lower() for loc in filters['locations']):
                return False, f"Location '{job_location}' not matching {filters['locations']}"
        else:
            return False, f"No location (need: {filters['locations']})"
    
    # Exclude by keywords
    if filters.get('exclude_keywords'):
        job_title = job.get('job_title') or job.get('title', '')
        job_title_lower = job_title.lower()
        for keyword in filters['exclude_keywords']:
            if keyword.lower() in job_title_lower:
                return False, f"Title contains excluded '{keyword}'"
    
    return True, "Passes all filters"


async def scrape_linkedin_jobs(keywords: str, location: str, limit: int, session_file: str, metrics: ScraperMetrics) -> List[dict]:
    """Scrape jobs from LinkedIn."""
    logger.info(f"Searching LinkedIn: {keywords} in {location}")
    
    try:
        async with BrowserManager(headless=True) as browser:
            await browser.load_session(session_file)
            
            # Search for job URLs
            callback = ConsoleCallback(verbose=False)
            search_scraper = JobSearchScraper(browser.page, callback=callback)
            
            job_urls = await search_scraper.search(
                keywords=keywords,
                location=location,
                limit=limit
            )
            
            logger.info(f"Found {len(job_urls)} LinkedIn job URLs")
            
            # Scrape full details with progress bar
            job_scraper = JobScraper(browser.page, callback=callback)
            jobs = []
            
            for job_url in tqdm(job_urls, desc="Scraping LinkedIn jobs"):
                try:
                    job = await job_scraper.scrape(job_url)
                    job_dict = job.to_dict()
                    job_dict['source'] = 'LinkedIn'
                    jobs.append(job_dict)
                    metrics.linkedin_jobs += 1
                    
                    await asyncio.sleep(SCRAPING_CONFIG['delays']['between_jobs'])
                except Exception as e:
                    logger.error(f"Error scraping LinkedIn job {job_url}: {e}")
                    metrics.errors.append(f"LinkedIn: {str(e)[:100]}")
                    continue
            
            logger.info(f"Scraped {len(jobs)} LinkedIn jobs")
            return jobs
            
    except Exception as e:
        logger.error(f"LinkedIn search failed: {e}")
        metrics.errors.append(f"LinkedIn search: {str(e)[:100]}")
        return []


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def fetch_jobserve_detail_async(session: aiohttp.ClientSession, job_url: str) -> Optional[str]:
    """Fetch JobServe job detail page asynchronously with retry."""
    try:
        async with session.get(job_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                return None
            
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            
            # Extract full job description using selector from config
            desc_elem = soup.select_one(JOBSERVE_SELECTORS['detail']['description'])
            return desc_elem.get_text(separator='\n', strip=True) if desc_elem else None
            
    except Exception as e:
        logger.debug(f"Error fetching detail page {job_url}: {e}")
        return None


async def scrape_jobserve_jobs_async(keywords: str, location: str, limit: int, jobserve_url: Optional[str], metrics: ScraperMetrics) -> List[dict]:
    """Scrape jobs from JobServe asynchronously."""
    logger.info(f"Searching JobServe: {keywords} in {location}")
    
    try:
        if jobserve_url:
            logger.info(f"Using direct URL: {jobserve_url[:80]}...")
            url = jobserve_url
        else:
            # Build JobServe search URL
            encoded_keywords = keywords.replace(' ', '+')
            encoded_location = location.replace(' ', '+')
            url = f"https://www.jobserve.com/gb/en/JobSearch.aspx?keywords={encoded_keywords}&location={encoded_location}"
            logger.info(f"Built URL: {url[:80]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        # Use aiohttp for async requests
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    logger.error(f"JobServe request failed: {response.status}")
                    return []
                
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
        
            # Extract job listings using selector from config
            job_listings = soup.select(JOBSERVE_SELECTORS['list']['job_listings'])
            
            logger.info(f"Found {len(job_listings)} JobServe listings")
            
            jobs = []
            for job_elem in tqdm(job_listings[:limit], desc="Processing JobServe jobs"):
                try:
                    # Extract using centralized selectors
                    title_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['title'])
                    title = title_elem.text.strip() if title_elem else 'Unknown'
                    
                    # URL
                    job_url = None
                    if title_elem and title_elem.get('href'):
                        href = title_elem['href']
                        job_url = href if href.startswith('http') else 'https://www.jobserve.com' + href
                    
                    # Location
                    loc_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['location'])
                    job_location = loc_elem.text.strip() if loc_elem else location
                    
                    # Salary
                    salary_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['salary'])
                    salary = salary_elem.text.strip() if salary_elem else None
                    
                    # Job type
                    type_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['type'])
                    job_type = type_elem.text.strip() if type_elem else 'Contract'
                    
                    # Posted date
                    date_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['posted_date'])
                    posted_date = date_elem.text.strip() if date_elem else None
                    
                    # Company - try Employment Business/Agency first
                    company = 'Unknown'
                    company_label = job_elem.find('label', string=re.compile(JOBSERVE_SELECTORS['list']['company_label']))
                    if company_label:
                        company_container = company_label.find_next('span', class_='jobListDetail')
                        if company_container:
                            company_link = company_container.find('a')
                            if company_link:
                                company = company_link.text.strip()
                    
                    # Fallback: Try to get from detail page if still Unknown
                    if company == 'Unknown' and job_url:
                        logger.debug(f"Fetching company from detail page for {title}")
                        try:
                            async with session.get(job_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                                if resp.status == 200:
                                    detail_html = await resp.text()
                                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                    # Look for "Posted by:" in detail page
                                    posted_by_elem = detail_soup.select_one(JOBSERVE_SELECTORS['detail']['posted_by'])
                                    if posted_by_elem:
                                        # Extract company name after "Posted by:"
                                        posted_by_text = posted_by_elem.get_text(strip=True)
                                        if 'Posted by:' in posted_by_text:
                                            company = posted_by_text.replace('Posted by:', '').strip()
                                            logger.debug(f"Got company from 'Posted by': {company}")
                        except Exception as e:
                            logger.debug(f"Could not fetch company from detail page: {e}")
                    
                    # Create job data
                    job_data = {
                        'job_title': title,
                        'company': company,
                        'location': job_location,
                        'employment_type': job_type,
                        'salary': salary,
                        'posted_date': posted_date,
                        'linkedin_url': job_url,
                        'job_description': None,
                        'source': 'JobServe'
                    }
                    
                    # Fetch full description asynchronously
                    if job_url:
                        full_desc = await fetch_jobserve_detail_async(session, job_url)
                        if full_desc:
                            job_data['job_description'] = full_desc
                            logger.debug(f"Got full description ({len(full_desc)} chars) for {title}")
                        else:
                            # Fallback to snippet
                            desc_elem = job_elem.select_one(JOBSERVE_SELECTORS['list']['snippet'])
                            job_data['job_description'] = desc_elem.text.strip() if desc_elem else None
                    
                    jobs.append(job_data)
                    metrics.jobserve_jobs += 1
                    
                    # Small delay between detail pages
                    await asyncio.sleep(SCRAPING_CONFIG['delays']['between_detail_pages'])
                    
                except Exception as e:
                    logger.error(f"Error parsing JobServe job: {e}")
                    metrics.errors.append(f"JobServe parse: {str(e)[:100]}")
                    continue
            
            logger.info(f"Scraped {len(jobs)} JobServe jobs")
            return jobs
        
    except Exception as e:
        logger.error(f"JobServe search failed: {e}")
        metrics.errors.append(f"JobServe search: {str(e)[:100]}")
        return []


async def run_search_cycle(config: ScraperConfig, seen_jobs: set, metrics: ScraperMetrics) -> List[dict]:
    """Run one complete search cycle across all platforms."""
    logger.info(f"Starting search cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_matching_jobs = []
    
    for search in config.searches:
        logger.info(f"Search: {search.keywords} in {search.location}")
        
        all_jobs = []
        
        # Search platforms
        if 'linkedin' in search.platforms:
            if not Path(config.linkedin_session_file).exists():
                logger.warning("Skipping LinkedIn - no session file")
            else:
                linkedin_jobs = await scrape_linkedin_jobs(
                    search.keywords, search.location,  search.limit,
                    config.linkedin_session_file, metrics
                )
                all_jobs.extend(linkedin_jobs)
        
        if 'jobserve' in search.platforms:
            jobserve_jobs = await scrape_jobserve_jobs_async(
                search.keywords, search.location, search.limit,
                search.jobserve_url, metrics
            )
            all_jobs.extend(jobserve_jobs)
        
        metrics.jobs_scraped += len(all_jobs)
        logger.info(f"Total jobs found: {len(all_jobs)}")
        logger.info("Filtering...")
        
        # Filter jobs
        for job in all_jobs:
            job_url = job.get('linkedin_url') or job.get('job_url', '')
            
            # Skip if already seen
            if job_url in seen_jobs:
                continue
            
            # Apply filters
            passes, reason = filter_job(job, config.filters.model_dump())
            
            if passes:
                all_matching_jobs.append(job)
                seen_jobs.add (job_url)
                metrics.jobs_matched += 1
                logger.info(f"MATCH: {job.get('job_title')} at {job.get('company')} [{job.get('source')}]")
            else:
                logger.debug(f"Filtered: {job.get('job_title')} - {reason}")
        
        # Delay between searches
        await asyncio.sleep(SCRAPING_CONFIG['delays']['between_searches'])
    
    return all_matching_jobs


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def send_job_to_webhook_async(job: dict, webhook_url: str, metrics: ScraperMetrics) -> bool:
    """Send a single job to webhook endpoint asynchronously with retry."""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "job_count": 1,
        "jobs": [job]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                str(webhook_url),
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status in [200, 201, 202]:
                    logger.info(f"Webhook success: {job['job_title']}")
                    metrics.webhook_successes += 1
                    return True
                else:
                    logger.warning(f"Webhook returned {response.status}")
                    metrics.webhook_failures += 1
                    return False
                    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        metrics.webhook_failures += 1
        metrics.errors.append(f"Webhook: {str(e)[:100]}")
        return False


async def send_jobs_to_webhook_async(jobs: List[dict], webhook_url: str, metrics: ScraperMetrics):
    """Send jobs to webhook endpoint one at a time asynchronously."""
    if not jobs:
        return
    
    logger.info(f"Sending {len(jobs)} jobs to webhook ONE AT A TIME...")
    
    for i, job in enumerate(tqdm(jobs, desc="Sending to webhook"), 1):
        await send_job_to_webhook_async(job, webhook_url, metrics)
        
        # Delay between jobs (except after the last one)
        if i < len(jobs):
            await asyncio.sleep(SCRAPING_CONFIG['delays']['webhook_send'])


async def save_results_async(jobs: List[dict], output_file: str, webhook_url: Optional[str], metrics: ScraperMetrics):
    """Save matching jobs to file and optionally send to webhook."""
    # Load existing data
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            data = json.load(f)
    else:
        data = {"last_updated": None, "total_jobs_found": 0, "jobs": []}
    
    # Add new jobs
    data['last_updated'] = datetime.now().isoformat()
    data['jobs'].extend(jobs)
    data['total_jobs_found'] = len(data['jobs'])
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved {len(jobs)} new jobs to {output_file}")
    logger.info(f"Total jobs in database: {data['total_jobs_found']}")
    
    # Send to webhook if configured
    if webhook_url:
        await send_jobs_to_webhook_async(jobs, webhook_url, metrics)


def print_summary(jobs: List[dict], metrics: ScraperMetrics):
    """Print summary of found jobs and metrics."""
    if not jobs:
        logger.info("No matching jobs found")
        print("\n📊 No matching jobs found")
        return
    
    # Group by source
    linkedin_jobs = [j for j in jobs if j.get('source') == 'LinkedIn']
    jobserve_jobs = [j for j in jobs if j.get('source') == 'JobServe']
    
    print(f"\n{'='*60}")
    print(f"📊 FOUND {len(jobs)} MATCHING JOBS")
    print(f"{'='*60}")
    print(f"   LinkedIn: {len(linkedin_jobs)} jobs")
    print(f"   JobServe: {len(jobserve_jobs)} jobs")
    print(f"\n   ⏱️  Duration: {metrics.duration():.1f}s")
    print(f"   📡 Webhook Success Rate: {metrics.webhook_successes}/{metrics.jobs_matched}")
    print(f"\n{'='*60}")
    
    for i, job in enumerate(jobs[:15], 1):
        source_emoji = "🔵" if job.get('source') == 'LinkedIn' else "🟢"
        print(f"\n{source_emoji} {i}. {job.get('job_title')}")
        print(f"   🏢 {job.get('company')}")
        print(f"   📍 {job.get('location')}")
        print(f"   📅 {job.get('posted_date')}")
        print(f"   💼 {job.get('employment_type')}")
        if job.get('salary'):
            print(f"   💰 {job.get('salary')}")
        print(f"   🔗 {job.get('linkedin_url') or job.get('job_url')}")
    
    if len(jobs) > 15:
        print(f"\n... and {len(jobs) - 15} more jobs")
    
    print(f"\n{'='*60}")


async def main():
    """Main function."""
    print("="*60)
    print("🤖 Multi-Platform Job Scraper (IMPROVED)")
    print("   LinkedIn + JobServe")
    print("="*60)
    
    # Initialize metrics
    metrics = ScraperMetrics()
    
    # Load and validate config
    config = load_config()
    
    print(f"\n⚙️  Configuration:")
    platforms = set(p for s in config.searches for p in s.platforms)
    print(f"   Platforms: {', '.join(platforms)}")
    print(f"   Searches: {len(config.searches)}")
    print(f"   Employment types: {config.filters.employment_types}")
    print(f"   Max posted days: {config.filters.max_posted_days_ago}")
    if config.webhook_url:
        print(f"   Webhook: {str(config.webhook_url)[:60]}...")
    
    # Track seen jobs
    seen_jobs = set()
    
    # Load existing
    if Path(config.output_file).exists():
        with open(config.output_file, 'r') as f:
            data = json.load(f)
            for job in data.get('jobs', []):
                url = job.get('linkedin_url') or job.get('job_url', '')
                if url:
                    seen_jobs.add(url)
        logger.info(f"Loaded {len(seen_jobs)} previously seen jobs")
    
    # Run search
    matching_jobs = await run_search_cycle(config, seen_jobs, metrics)
    
    # Save and display
    if matching_jobs:
        await save_results_async(matching_jobs, config.output_file, config.webhook_url, metrics)
        print_summary(matching_jobs, metrics)
    else:
        logger.info("No new matching jobs found")
        print("\n📊 No new matching jobs found")
    
    # Save metrics
    metrics.save_to_file()
    
    # Print final metrics
    print(f"\n{'='*60}")
    print("📈 SCRAPING METRICS")
    print(f"{'='*60}")
    print(f"   Duration: {metrics.duration():.1f}s")
    print(f"   Jobs Scraped: {metrics.jobs_scraped}")
    print(f"   Jobs Matched: {metrics.jobs_matched}")
    print(f"   LinkedIn: {metrics.linkedin_jobs}")
    print(f"   JobServe: {metrics.jobserve_jobs}")
    print(f"   Webhook Successes: {metrics.webhook_successes}")
    print(f"   Webhook Failures: {metrics.webhook_failures}")
    if metrics.errors:
        print(f"   Errors: {len(metrics.errors)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        print("\n\n⚠️  Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()