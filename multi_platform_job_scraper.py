#!/usr/bin/env python3
"""
Multi-Platform Job Scraper - LinkedIn + JobServe

Searches both LinkedIn and JobServe with unified filtering.
Configure via multi_platform_config.json
"""

import asyncio
import json
import sys
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

from linkedin_scraper import BrowserManager, JobSearchScraper, JobScraper, ConsoleCallback


def load_config(config_file: str = "multi_platform_config.json") -> dict:
    """Load configuration from JSON file."""
    if not Path(config_file).exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        return json.load(f)


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


async def scrape_linkedin_jobs(keywords: str, location: str, limit: int, session_file: str) -> List[dict]:
    """Scrape jobs from LinkedIn."""
    print(f"\n🔵 Searching LinkedIn: {keywords} in {location}")
    
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
            
            print(f"   Found {len(job_urls)} LinkedIn job URLs")
            
            # Scrape full details
            job_scraper = JobScraper(browser.page, callback=callback)
            jobs = []
            
            for i, job_url in enumerate(job_urls, 1):
                try:
                    print(f"   [{i}/{len(job_urls)}] Scraping LinkedIn job...")
                    job = await job_scraper.scrape(job_url)
                    job_dict = job.to_dict()
                    job_dict['source'] = 'LinkedIn'
                    jobs.append(job_dict)
                    
                    if i < len(job_urls):
                        await asyncio.sleep(2)
                except Exception as e:
                    print(f"      Error: {e}")
                    continue
            
            print(f"   ✅ Scraped {len(jobs)} LinkedIn jobs")
            return jobs
            
    except Exception as e:
        print(f"   ❌ LinkedIn search failed: {e}")
        return []


def scrape_jobserve_detail_page(job_url: str) -> Optional[dict]:
    """Scrape full details from a JobServe job detail page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(job_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract full job description from md_skills
        desc_elem = soup.select_one('#md_skills, div.md_skills')
        full_description = desc_elem.get_text(separator='\n', strip=True) if desc_elem else None
        
        return {"job_description": full_description}
        
    except Exception as e:
        print(f"      Error fetching detail page: {e}")
        return None


def scrape_jobserve_jobs(keywords: str, location: str, limit: int, jobserve_url: Optional[str] = None) -> List[dict]:
    """Scrape jobs from JobServe."""
    print(f"\n🟢 Searching JobServe: {keywords} in {location}")
    
    try:
        if jobserve_url:
            print(f"   Using direct URL: {jobserve_url}")
            url = jobserve_url
        else:
            # Build JobServe search URL
            # Note: You may need to construct this based on JobServe's URL structure
            encoded_keywords = keywords.replace(' ', '+')
            encoded_location = location.replace(' ', '+')
            url = f"https://www.jobserve.com/gb/en/JobSearch.aspx?keywords={encoded_keywords}&location={encoded_location}"
            print(f"   Built URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ Request failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple selectors for job listings
        job_listings = soup.select('#jsJobResContent .jobItem')
        if not job_listings:
            job_listings = soup.select('div.jobListItem')
        if not job_listings:
            job_listings = soup.select('div.jobItem')
        
        print(f"   Found {len(job_listings)} JobServe listings")
        
        jobs = []
        for job_elem in job_listings[:limit]:
            try:
                # Extract job details
                job_id = job_elem.get('id', '')
                
                # Title - in a.jobListPosition
                title_elem = job_elem.select_one('a.jobListPosition')
                title = title_elem.text.strip() if title_elem else 'Unknown'
                
                # URL - from title link
                job_url = None
                if title_elem and title_elem.get('href'):
                    href = title_elem['href']
                    if href.startswith('http'):
                        job_url = href
                    else:
                        job_url = 'https://www.jobserve.com' + href
                
                # Location - span#summlocation
                loc_elem = job_elem.select_one('span[id*="location"]')
                job_location = loc_elem.text.strip() if loc_elem else location
                
                # Salary - span#summrate
                salary_elem = job_elem.select_one('span[id*="rate"]')
                salary = salary_elem.text.strip() if salary_elem else None
                
                # Job type - span#summtype
                type_elem = job_elem.select_one('span[id*="type"]')
                job_type = type_elem.text.strip() if type_elem else 'Contract'
                
                # Posted date - span#summposteddate
                date_elem = job_elem.select_one('span[id*="posteddate"]')
                posted_date = date_elem.text.strip() if date_elem else None
                
                # Company - Employment Business/Agency link
                company = 'Unknown'
                company_label = job_elem.find('label', string=re.compile('Employment Business|Employment Agency'))
                if company_label:
                    company_container = company_label.find_next('span', class_='jobListDetail')
                    if company_container:
                        company_link = company_container.find('a')
                        if company_link:
                            company = company_link.text.strip()
                
                # Create job dict with initial data
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
                
                # Fetch full description from detail page
                if job_url:
                    print(f"      Fetching full description...")
                    detail_data = scrape_jobserve_detail_page(job_url)
                    if detail_data and detail_data.get('job_description'):
                        job_data['job_description'] = detail_data['job_description']
                        print(f"      ✅ Got full description ({len(job_data['job_description'])} chars)")
                    else:
                        # Fallback to snippet
                        desc_elem = job_elem.select_one('p.jobListSkills')
                        job_data['job_description'] = desc_elem.text.strip() if desc_elem else None
                
                jobs.append(job_data)
                
                # Small delay between detail page fetches
                time.sleep(1)
                
            except Exception as e:
                print(f"   Error parsing job: {e}")
                continue
        
        print(f"   ✅ Scraped {len(jobs)} JobServe jobs")
        return jobs
        
    except Exception as e:
        print(f"   ❌ JobServe search failed: {e}")
        return []


async def run_search_cycle(config: dict, seen_jobs: set) -> List[dict]:
    """Run one complete search cycle across all platforms."""
    print(f"\n{'='*60}")
    print(f"🚀 Starting search cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    all_matching_jobs = []
    
    for search in config['searches']:
        keywords = search['keywords']
        location = search['location']
        limit = search.get('limit', 50)
        
        print(f"\n{'='*60}")
        print(f"📋 Search: {keywords} in {location}")
        print(f"{'='*60}")
        
        all_jobs = []
        
        # Search platforms
        platforms = search.get('platforms', ['linkedin', 'jobserve'])
        
        if 'linkedin' in platforms:
            if not Path(config.get('linkedin_session_file', 'session.json')).exists():
                print("⚠️  Skipping LinkedIn - no session file")
            else:
                linkedin_jobs = await scrape_linkedin_jobs(
                    keywords, location, limit,
                    config.get('linkedin_session_file', 'session.json')
                )
                all_jobs.extend(linkedin_jobs)
        
        if 'jobserve' in platforms:
            jobserve_url = search.get('jobserve_url')
            jobserve_jobs = scrape_jobserve_jobs(keywords, location, limit, jobserve_url)
            all_jobs.extend(jobserve_jobs)
        
        print(f"\n📊 Total jobs found: {len(all_jobs)}")
        print(f"   Filtering...")
        
        # Filter jobs
        for job in all_jobs:
            job_url = job.get('linkedin_url') or job.get('job_url', '')
            
            # Skip if already seen
            if job_url in seen_jobs:
                continue
            
            # Apply filters
            passes, reason = filter_job(job, config['filters'])
            
            if passes:
                all_matching_jobs.append(job)
                seen_jobs.add(job_url)
                print(f"   ✅ MATCH: {job.get('job_title')} at {job.get('company')} [{job.get('source')}]")
            else:
                print(f"   ❌ Filtered: {job.get('job_title')} - {reason}")
        
        # Small delay between searches
        await asyncio.sleep(3)
    
    return all_matching_jobs


def send_job_to_webhook(job: dict, webhook_url: str) -> bool:
    """Send a single job to webhook endpoint."""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "job_count": 1,
        "jobs": [job]
    }
    
    try:
        print(f"\n📡 Sending job: {job['job_title']}")
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code in [200, 201, 202]:
            print(f"   ✅ Webhook successful (status: {response.status_code})")
            return True
        else:
            print(f"   ⚠️  Webhook returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ⚠️  Webhook error: {e}")
        return False


def send_jobs_to_webhook_one_by_one(jobs: List[dict], webhook_url: str, delay_seconds: int = 2):
    """Send jobs to webhook endpoint one at a time with delays."""
    if not jobs:
        return
    
    print(f"\n📡 Sending {len(jobs)} jobs to webhook ONE AT A TIME...")
    print(f"   Delay between sends: {delay_seconds} seconds\n")
    
    success_count = 0
    for i, job in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] ", end="")
        
        if send_job_to_webhook(job, webhook_url):
            success_count += 1
        
        # Delay between jobs (except after the last one)
        if i < len(jobs):
            print(f"   ⏳ Waiting {delay_seconds} seconds...")
            time.sleep(delay_seconds)
    
    print(f"\n✅ Successfully sent {success_count}/{len(jobs)} jobs to webhook")


def save_results(jobs: List[dict], output_file: str, webhook_url: Optional[str] = None):
    """Save matching jobs to file and optionally send to webhook."""
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            data = json.load(f)
    else:
        data = {"last_updated": None, "total_jobs_found": 0, "jobs": []}
    
    data['last_updated'] = datetime.now().isoformat()
    data['jobs'].extend(jobs)
    data['total_jobs_found'] = len(data['jobs'])
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n💾 Saved {len(jobs)} new jobs to {output_file}")
    print(f"   Total jobs in database: {data['total_jobs_found']}")
    
    # Send to webhook if configured (one job at a time)
    if webhook_url:
        send_jobs_to_webhook_one_by_one(jobs, webhook_url, delay_seconds=2)


def print_summary(jobs: List[dict]):
    """Print summary of found jobs."""
    if not jobs:
        print("\n📊 No matching jobs found")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 FOUND {len(jobs)} MATCHING JOBS")
    print(f"{'='*60}")
    
    # Group by source
    linkedin_jobs = [j for j in jobs if j.get('source') == 'LinkedIn']
    jobserve_jobs = [j for j in jobs if j.get('source') == 'JobServe']
    
    print(f"   LinkedIn: {len(linkedin_jobs)} jobs")
    print(f"   JobServe: {len(jobserve_jobs)} jobs")
    
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
    print("🤖 Multi-Platform Job Scraper")
    print("   LinkedIn + JobServe")
    print("="*60)
    
    config = load_config()
    
    print(f"\n⚙️  Configuration:")
    print(f"   Platforms: {', '.join(set(p for s in config['searches'] for p in s.get('platforms', ['linkedin'])))}")
    print(f"   Searches: {len(config['searches'])}")
    print(f"   Employment types: {config['filters'].get('employment_types', ['Any'])}")
    print(f"   Max posted days: {config['filters'].get('max_posted_days_ago', 'Any')}")
    
    # Track seen jobs
    seen_jobs = set()
    
    # Load existing
    if Path(config['output_file']).exists():
        with open(config['output_file'], 'r') as f:
            data = json.load(f)
            for job in data.get('jobs', []):
                url = job.get('linkedin_url') or job.get('job_url', '')
                if url:
                    seen_jobs.add(url)
        print(f"   Previously seen: {len(seen_jobs)} jobs")
    
    # Run search
    matching_jobs = await run_search_cycle(config, seen_jobs)
    
    # Save and display
    if matching_jobs:
        save_results(matching_jobs, config['output_file'], config.get('webhook_url'))
        print_summary(matching_jobs)
    else:
        print("\n📊 No new matching jobs found")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
