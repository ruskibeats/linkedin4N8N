#!/usr/bin/env python3
"""
JobServe Job Scraper

Scrapes jobs from JobServe.com search results.
Works with JobServe search URLs.
"""

import asyncio
import json
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


def scrape_jobserve_search(jobserve_url: str, max_pages: int = 5) -> List[dict]:
    """
    Scrape jobs from a JobServe search URL.
    
    Args:
        jobserve_url: JobServe search URL (e.g., https://www.jobserve.com/gb/en/JobListing.aspx?shid=...)
        max_pages: Maximum number of pages to scrape
    
    Returns:
        List of job dictionaries
    """
    print(f"\n{'='*60}")
    print(f"🟢 Scraping JobServe")
    print(f"{'='*60}")
    print(f"URL: {jobserve_url}")
    
    jobs = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    }
    
    for page in range(1, max_pages + 1):
        print(f"\n📄 Scraping page {page}...")
        
        # Build page URL
        if page == 1:
            page_url = jobserve_url
        else:
            # JobServe uses page parameter in URL
            if '&page=' in jobserve_url:
                page_url = re.sub(r'&page=\d+', f'&page={page}', jobserve_url)
            else:
                page_url = f"{jobserve_url}&page={page}"
        
        try:
            response = requests.get(page_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"   ❌ Request failed: {response.status_code}")
                break
            
            # Save HTML for debugging
            with open(f'jobserve_page_{page}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"   Saved HTML to jobserve_page_{page}.html")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract jobs from page
            page_jobs = extract_jobs_from_page(soup, page_url)
            
            if not page_jobs:
                print(f"   No jobs found on page {page}, stopping")
                break
            
            print(f"   ✅ Found {len(page_jobs)} jobs on page {page}")
            jobs.extend(page_jobs)
            
            # Stop if we got fewer jobs than expected (last page)
            if len(page_jobs) < 20:
                print(f"   Last page (fewer than 20 jobs)")
                break
            
        except Exception as e:
            print(f"   ❌ Error scraping page {page}: {e}")
            break
    
    print(f"\n✅ Total JobServe jobs scraped: {len(jobs)}")
    return jobs


def extract_jobs_from_page(soup: BeautifulSoup, page_url: str) -> List[dict]:
    """Extract job listings from JobServe page."""
    jobs = []
    
    # JobServe uses div.jobListItem
    job_listings = soup.select('div.jobListItem')
    
    print(f"      Found {len(job_listings)} job elements")
    
    for job_elem in job_listings:
        try:
            job = extract_job_details(job_elem)
            if job:
                jobs.append(job)
        except Exception as e:
            print(f"      Error extracting job: {e}")
            continue
    
    return jobs


def extract_job_details(job_elem) -> Optional[dict]:
    """Extract details from a single job element."""
    try:
        # Job ID
        job_id = job_elem.get('id', '')
        
        # Title - in a.jobListPosition
        title_elem = job_elem.select_one('a.jobListPosition')
        if not title_elem:
            return None
        title = title_elem.text.strip()
        
        # URL - from the title link
        job_url = None
        if title_elem and 'href' in title_elem.attrs:
            href = title_elem['href']
            if href.startswith('http'):
                job_url = href
            else:
                job_url = 'https://www.jobserve.com' + href
        
        # Company - from branding image or agency name
        company = 'Unknown'
        # Check for agency/company info
        agency_elem = job_elem.select_one('span[id*="agency"], span.jobListAgency')
        if agency_elem:
            company = agency_elem.text.strip()
        else:
            # Try to get from branding image alt text
            img = job_elem.select_one('img.jobListBrandingImage')
            if img and img.get('alt'):
                company = img.get('alt')
        
        # Location - in span with id="summlocation"
        location_elem = job_elem.select_one('span[id*="location"]')
        location = location_elem.text.strip() if location_elem else 'Unknown'
        
        # Salary - in span with id="summrate" or id containing "rate"
        salary_elem = job_elem.select_one('span[id*="rate"], span[id*="salary"]')
        salary = salary_elem.text.strip() if salary_elem else None
        
        # Job type - in span with id containing "type"
        type_elem = job_elem.select_one('span[id*="type"]')
        job_type_text = type_elem.text.strip() if type_elem else ''
        
        # Determine employment type
        if 'Contract' in job_type_text or 'Contract' in title:
            employment_type = 'Contract'
        elif 'Permanent' in job_type_text or 'Perm' in job_type_text:
            employment_type = 'Permanent'
        else:
            # Default to Contract for JobServe (most are contract)
            employment_type = 'Contract'
        
        # Posted date - look for "when" or date elements
        date_elem = job_elem.select_one('span[id*="when"], span.when, time')
        posted_date = date_elem.text.strip() if date_elem else None
        
        # Description - in jobListSnippet or similar
        desc_elem = job_elem.select_one('div.jobListSnippet, span.jobListSnippet, div[id*="snippet"]')
        description = desc_elem.text.strip() if desc_elem else None
        
        return {
            'job_title': title,
            'company': company,
            'location': location,
            'employment_type': employment_type,
            'salary': salary,
            'posted_date': posted_date,
            'job_description': description,
            'linkedin_url': job_url,
            'source': 'JobServe',
            'applicant_count': None,
            'company_linkedin_url': None
        }
        
    except Exception as e:
        print(f"         Error in extract_job_details: {e}")
        return None


def parse_posted_date(posted_date: str) -> Optional[int]:
    """Parse posted date to days ago."""
    if not posted_date:
        return None
    
    posted_date = posted_date.lower()
    match = re.search(r'(\d+)', posted_date)
    if not match:
        return None
    
    num = int(match.group(1))
    
    if 'hour' in posted_date or 'hr' in posted_date:
        return 0 if num < 24 else 1
    elif 'day' in posted_date:
        return num
    elif 'week' in posted_date or 'wk' in posted_date:
        return num * 7
    elif 'month' in posted_date:
        return num * 30
    
    return None


def filter_job(job: dict, filters: dict) -> tuple[bool, str]:
    """Check if job matches filters."""
    # Posted date - allow jobs without dates to pass through
    if filters.get('max_posted_days_ago'):
        posted_date = job.get('posted_date', '')
        if posted_date:  # Only filter if date exists
            days_ago = parse_posted_date(posted_date)
            if days_ago and days_ago > filters['max_posted_days_ago']:
                return False, f"Posted {days_ago} days ago (max: {filters['max_posted_days_ago']})"
    
    # Employment type
    if filters.get('employment_types'):
        job_type = job.get('employment_type')
        if not job_type:
            return False, "No employment type"
        if job_type.lower() not in [t.lower() for t in filters['employment_types']]:
            return False, f"Type '{job_type}' not in {filters['employment_types']}"
    
    # Location
    if filters.get('locations'):
        job_location = job.get('location', '')
        if not job_location or job_location == 'Unknown':
            return False, "No location"
        if not any(loc.lower() in job_location.lower() for loc in filters['locations']):
            return False, f"Location '{job_location}' not in {filters['locations']}"
    
    # Exclude keywords
    if filters.get('exclude_keywords'):
        title = job.get('job_title', '').lower()
        for keyword in filters['exclude_keywords']:
            if keyword.lower() in title:
                return False, f"Contains excluded keyword '{keyword}'"
    
    return True, "Passes all filters"


def main():
    """Main function."""
    print("="*60)
    print("🟢 JobServe Job Scraper")
    print("="*60)
    
    # Configuration
    JOBSERVE_URL = "https://www.jobserve.com/gb/en/JobListing.aspx?shid=EDEFD31A1D5DFE53D094&js=1&jsdiag=1"
    OUTPUT_FILE = "jobserve_jobs.json"
    MAX_PAGES = 3
    
    FILTERS = {
        "max_posted_days_ago": 7,
        "employment_types": ["Contract"],
        "locations": ["United Kingdom", "UK", "England", "London", "Remote"],
        "exclude_keywords": []
    }
    
    print(f"\n⚙️  Configuration:")
    print(f"   Max pages: {MAX_PAGES}")
    print(f"   Employment types: {FILTERS['employment_types']}")
    print(f"   Max posted days: {FILTERS['max_posted_days_ago']}")
    
    # Scrape jobs
    all_jobs = scrape_jobserve_search(JOBSERVE_URL, MAX_PAGES)
    
    if not all_jobs:
        print("\n❌ No jobs found")
        return
    
    # Filter jobs
    print(f"\n{'='*60}")
    print(f"🔍 Filtering {len(all_jobs)} jobs...")
    print(f"{'='*60}")
    
    matching_jobs = []
    for job in all_jobs:
        passes, reason = filter_job(job, FILTERS)
        if passes:
            matching_jobs.append(job)
            print(f"✅ MATCH: {job['job_title']}")
        else:
            print(f"❌ {job['job_title']} - {reason}")
    
    # Save results
    output_data = {
        "last_updated": datetime.now().isoformat(),
        "total_jobs_found": len(matching_jobs),
        "search_url": JOBSERVE_URL,
        "filters_applied": FILTERS,
        "jobs": matching_jobs
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS")
    print(f"{'='*60}")
    print(f"   Total found: {len(all_jobs)}")
    print(f"   Matching filters: {len(matching_jobs)}")
    print(f"   Saved to: {OUTPUT_FILE}")
    
    # Print sample
    if matching_jobs:
        print(f"\n{'='*60}")
        print("📋 Sample Jobs:")
        print(f"{'='*60}")
        for i, job in enumerate(matching_jobs[:5], 1):
            print(f"\n{i}. {job['job_title']}")
            print(f"   🏢 {job['company']}")
            print(f"   📍 {job['location']}")
            print(f"   💼 {job['employment_type']}")
            if job.get('salary'):
                print(f"   💰 {job['salary']}")
            if job.get('posted_date'):
                print(f"   📅 {job['posted_date']}")
            if job.get('linkedin_url'):
                print(f"   🔗 {job['linkedin_url']}")


if __name__ == "__main__":
    main()
