#!/usr/bin/env python3
"""
Indeed Job Scraper using jobspy library

This uses the jobspy library for reliable Indeed scraping with built-in anti-bot handling.
More reliable than direct HTTP requests.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import requests
from jobspy import scrape_jobs

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndeedDrone")


def load_config(config_file: str = "multi_platform_config.json") -> dict:
    """Load configuration from JSON file."""
    if not Path(config_file).exists():
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    with open(config_file, 'r') as f:
        return json.load(f)


def filter_job(job: dict, filters: dict) -> bool:
    """Check if job matches filter criteria."""
    # Filter by employment type
    if filters.get('employment_types'):
        job_type = job.get('employment_type')
        if job_type and not isinstance(job_type, float):  # Skip NaN (floats in pandas)
            job_type_str = str(job_type).lower().replace("-", "").replace(" ", "")
            filter_types_normalized = [str(t).lower().replace("-", "").replace(" ", "") for t in filters['employment_types']]
            if not any(ft in job_type_str for ft in filter_types_normalized):
                # logger.debug(f"Rejecting {job.get('job_title')}: type '{job_type}' not in {filters['employment_types']}")
                return False
    
    # Filter by location
    if filters.get('locations'):
        job_location = job.get('location', '')
        if job_location and not isinstance(job_location, float):
            job_location_str = str(job_location).lower()
            if not any(str(loc).lower() in job_location_str for loc in filters['locations']):
                # logger.debug(f"Rejecting {job.get('job_title')}: location '{job_location}' not in {filters['locations']}")
                return False
        else:
            # logger.debug(f"Rejecting {job.get('job_title')}: no location or NaN")
            return False
                
    # Exclude by keywords
    if filters.get('exclude_keywords'):
        job_title = str(job.get('job_title', '') or '').lower()
        for keyword in filters['exclude_keywords']:
            if str(keyword).lower() in job_title:
                return False
                
    return True


def send_to_webhook(job: dict, webhook_url: str) -> bool:
    """Send job to webhook endpoint."""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "job_count": 1,
        "jobs": [job]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Sent to n8n: {job['job_title']}")
            return True
        else:
            logger.warning(f"⚠️ Webhook error {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Webhook failed: {e}")
        return False


async def run_jobspy_indeed_search(config_file: str = "multi_platform_config.json", webhook_url: Optional[str] = None):
    """
    Run Indeed search using jobspy library.
    
    Args:
        config_file: Path to configuration JSON file
        webhook_url: Optional override webhook URL
    
    Returns:
        List of matching job dictionaries
    """
    config = load_config(config_file)
    
    # Use provided webhook or fall back to config
    webhook_url = webhook_url or config.get('webhook_url')
    
    # Load seen jobs
    seen_jobs = set()
    output_file = config.get('output_file', 'multi_platform_jobs.json')
    if Path(output_file).exists():
        try:
            with open(output_file, 'r') as f:
                data = json.load(f)
                seen_jobs = {j.get('job_url') for j in data.get('jobs', []) if j.get('job_url')}
        except:
            pass

    new_jobs_list = []

    for search in config['searches']:
        # Only run if indeed is in platforms
        if 'indeed' not in search.get('platforms', []):
            logger.info(f"⏭️  Skipping Indeed (not in platforms)")
            continue
            
        keywords = search['keywords']
        location = search['location']
        limit = search.get('limit', 20)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🟡 Searching Indeed: {keywords} in {location}")
        logger.info(f"{'='*60}")
        
        try:
            # Using jobspy to scrape indeed
            results = scrape_jobs(
                site_name=["indeed"],
                search_term=keywords,
                location=location,
                results_wanted=limit,
                country_indeed='uk' 
            )
            
            if results.empty:
                logger.info(f"⚠️  No jobs found on Indeed for {keywords}.")
                continue
            
            logger.info(f"✅ Found {len(results)} jobs on Indeed.")

            for i, (_, row) in enumerate(results.iterrows(), 1):
                job_url = row.get('job_url')
                if job_url in seen_jobs:
                    logger.info(f"   [{i}/{len(results)}] Skipping duplicate")
                    continue
                
                # Map jobspy fields to your n8n schema
                def clean(val):
                    if isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf')):
                        return None
                    return val if val is not None else None

                job_data = {
                    "job_title": clean(row.get('title')),
                    "company": clean(row.get('company')),
                    "location": clean(row.get('location')),
                    "employment_type": clean(row.get('job_type')),
                    "salary": str(row.get('compensation')) if row.get('compensation') and not isinstance(row.get('compensation'), float) else None,
                    "posted_date": str(row.get('date_posted')) if row.get('date_posted') and not isinstance(row.get('date_posted'), float) else None,
                    "job_url": clean(job_url),
                    "linkedin_url": clean(job_url),
                    "job_description": clean(row.get('description')),
                    "source": "Indeed"
                }

                # Second pass to catch any remaining 'nan' strings or floats
                job_data = {k: (None if (v == 'nan' or (isinstance(v, float) and v != v)) else v) for k, v in job_data.items()}

                if filter_job(job_data, config['filters']):
                    logger.info(f"✨ [{i}/{len(results)}] Match: {job_data['job_title']} at {job_data['company']}")
                    new_jobs_list.append(job_data)
                    seen_jobs.add(job_url)
                    
                    if webhook_url:
                        if send_to_webhook(job_data, webhook_url):
                            # Delay between webhook sends
                            await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"❌ Error scraping Indeed: {e}")
            import traceback
            traceback.print_exc()

    # Save results back to multi_platform_jobs.json
    if new_jobs_list:
        if Path(output_file).exists():
            with open(output_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"last_updated": None, "jobs": []}
            
        data['last_updated'] = datetime.now().isoformat()
        data['jobs'].extend(new_jobs_list)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"\n💾 Saved {len(new_jobs_list)} new Indeed jobs to {output_file}")
    else:
        logger.info(f"\n📊 No new Indeed jobs found")
    
    return new_jobs_list


async def main():
    """Main function for testing."""
    config_file = "data_engineer_config.json"
    logger.info("="*60)
    logger.info("🟡 jobspy Indeed Scraper Test")
    logger.info("="*60)
    
    jobs = await run_jobspy_indeed_search(config_file)
    
    if jobs:
        logger.info(f"\n✅ Total Indeed jobs found: {len(jobs)}")
        for i, job in enumerate(jobs[:5], 1):
            logger.info(f"\n{i}. {job.get('job_title')}")
            logger.info(f"   🏢 {job.get('company')}")
            logger.info(f"   📍 {job.get('location')}")
            logger.info(f"   💼 {job.get('employment_type')}")
            logger.info(f"   💰 {job.get('salary')}")
            logger.info(f"   📅 {job.get('posted_date')}")
            logger.info(f"   🔗 {job.get('job_url')}")
        
        if len(jobs) > 5:
            logger.info(f"\n... and {len(jobs) - 5} more jobs")
    else:
        logger.info("\n❌ No jobs found")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()