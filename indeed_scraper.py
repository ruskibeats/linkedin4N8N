#!/usr/bin/env python3
"""
Indeed Job Scraper

Scrapes job listings from Indeed.com with support for filtering and webhook integration.
Can be integrated into multi-platform job scraper.
"""

import asyncio
import json
import re
import time
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


def scrape_indeed_jobs(keywords: str, location: str, limit: int = 50) -> List[dict]:
    """
    Scrape jobs from Indeed.com.
    
    Args:
        keywords: Job search keywords
        location: Job location
        limit: Maximum number of jobs to return
    
    Returns:
        List of job dictionaries
    """
    print(f"\n🟡 Searching Indeed: {keywords} in {location}")
    
    # Build Indeed search URL
    encoded_keywords = keywords.replace(' ', '+')
    encoded_location = location.replace(' ', '+')
    url = f"https://www.indeed.com/jobs?q={encoded_keywords}&l={encoded_location}"
    
    # More realistic headers to avoid blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
    }
    
    try:
        # Add random delay to avoid rate limiting
        time.sleep(2)
        
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        if response.status_code != 200:
            if response.status_code == 403:
                print(f"   ❌ Indeed blocked request (403 Forbidden)")
                print(f"   💡 Suggestion: Indeed has strong anti-bot measures")
                print(f"   💡 Try: Using a VPN or different IP address")
                print(f"   💡 Consider: Using the Indeed API instead of scraping")
            elif response.status_code == 429:
                print(f"   ❌ Rate limited (429 Too Many Requests)")
                print(f"   💡 Suggestion: Wait longer between requests")
                print(f"   💡 Try: Reducing request frequency")
            else:
                print(f"   ❌ Request failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find job cards
        job_cards = soup.select('div.job_seen_bj0NPKo37T6eQ')
        if not job_cards:
            # Try alternative selectors
            job_cards = soup.select('div.jobCard')
            if not job_cards:
                job_cards = soup.select('td.resultContent')
        
        print(f"   Found {len(job_cards)} Indeed job listings")
        
        jobs = []
        for i, card in enumerate(job_cards[:limit], 1):
            try:
                # Extract job details
                job_data = parse_job_card(card)
                if job_data:
                    job_data['source'] = 'Indeed'
                    jobs.append(job_data)
                    print(f"   [{i}/{min(len(job_cards), limit)}] Scraped: {job_data.get('job_title', 'Unknown')}")
                
                # Small delay between scrapes
                if i < len(job_cards[:limit]):
                    time.sleep(1)
                    
            except Exception as e:
                print(f"      Error parsing job: {e}")
                continue
        
        print(f"   ✅ Scraped {len(jobs)} Indeed jobs")
        return jobs
        
    except Exception as e:
        print(f"   ❌ Indeed search failed: {e}")
        return []


def parse_job_card(card) -> Optional[dict]:
    """
    Parse a single job card from Indeed.
    
    Args:
        card: BeautifulSoup element for a job card
    
    Returns:
        Job dictionary or None
    """
    try:
        # Job title - h2.jobTitle
        title_elem = card.select_one('h2.jobTitle')
        if not title_elem:
            title_elem = card.select_one('a.jobTitle')
        title = title_elem.text.strip() if title_elem else 'Unknown'
        
        # Company - span.companyName
        company_elem = card.select_one('span.companyName')
        company = company_elem.text.strip() if company_elem else 'Unknown'
        
        # Location - div.companyLocation
        location_elem = card.select_one('div.companyLocation')
        location = location_elem.text.strip() if location_elem else None
        
        # Salary - span.salary-snippet
        salary_elem = card.select_one('span.salary-snippet')
        salary = salary_elem.text.strip() if salary_elem else None
        
        # Job URL - a.jobtitle
        link_elem = card.select_one('a.jobtitle') or card.select_one('h2.jobTitle > a')
        job_url = None
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            if href.startswith('http'):
                job_url = href
            elif href.startswith('/'):
                job_url = 'https://www.indeed.com' + href
        
        # Job description snippet - div.job-snippet
        desc_elem = card.select_one('div.job-snippet')
        description = desc_elem.text.strip() if desc_elem else None
        
        # Posted date - span.date
        date_elem = card.select_one('span.date')
        posted_date = date_elem.text.strip() if date_elem else None
        
        return {
            'job_title': title,
            'company': company,
            'location': location,
            'salary': salary,
            'linkedin_url': job_url,
            'job_description': description,
            'posted_date': posted_date,
        }
        
    except Exception as e:
        print(f"      Error parsing job card: {e}")
        return None


def parse_posted_date(posted_date: str) -> Optional[int]:
    """
    Parse Indeed posted date to days ago.
    
    Args:
        posted_date: String like "2 days ago", "1 week ago"
    
    Returns:
        Days ago as integer
    """
    if not posted_date:
        return None
    
    posted_date = posted_date.lower()
    
    if 'day' in posted_date:
        match = re.search(r'(\d+)\s+day', posted_date)
        if match:
            return int(match.group(1))
    elif 'week' in posted_date:
        match = re.search(r'(\d+)\s+week', posted_date)
        if match:
            return int(match.group(1)) * 7
    elif 'month' in posted_date:
        match = re.search(r'(\d+)\s+month', posted_date)
        if match:
            return int(match.group(1)) * 30
    elif 'hour' in posted_date:
        return 0 if 'hour' in posted_date else 1
    
    return None


def filter_job(job: dict, filters: dict) -> tuple[bool, str]:
    """
    Check if job matches filter criteria.
    
    Args:
        job: Job dictionary
        filters: Filter criteria
    
    Returns:
        Tuple of (passes, reason)
    """
    # Filter by posted date
    if filters.get('max_posted_days_ago'):
        days_ago = parse_posted_date(job.get('posted_date', ''))
        if days_ago is None or days_ago > filters['max_posted_days_ago']:
            return False, f"Posted {days_ago} days ago (max: {filters['max_posted_days_ago']})"
    
    # Filter by employment type
    if filters.get('employment_types'):
        # Indeed doesn't always show employment type, so we might not filter this
        pass
    
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
        job_title = job.get('job_title', '')
        job_title_lower = job_title.lower()
        for keyword in filters['exclude_keywords']:
            if keyword.lower() in job_title_lower:
                return False, f"Title contains excluded '{keyword}'"
    
    return True, "Passes all filters"


async def main():
    """Main function for testing Indeed scraper."""
    print("="*60)
    print("🟡 Indeed Job Scraper Test")
    print("="*60)
    
    # Test scrape
    keywords = "programme manager project manager"
    location = "London"
    limit = 10
    
    jobs = scrape_indeed_jobs(keywords, location, limit)
    
    if jobs:
        print(f"\n✅ Found {len(jobs)} jobs")
        print("\n" + "="*60)
        for i, job in enumerate(jobs[:5], 1):
            print(f"\n{i}. {job.get('job_title')}")
            print(f"   🏢 {job.get('company')}")
            print(f"   📍 {job.get('location')}")
            print(f"   💰 {job.get('salary')}")
            print(f"   📅 {job.get('posted_date')}")
            print(f"   🔗 {job.get('linkedin_url')}")
        
        if len(jobs) > 5:
            print(f"\n... and {len(jobs) - 5} more jobs")
        
        print("\n" + "="*60)
    else:
        print("\n❌ No jobs found")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()