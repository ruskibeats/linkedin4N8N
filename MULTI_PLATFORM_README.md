# Multi-Platform Job Scraper

Comprehensive job scraper that searches multiple job boards (LinkedIn, JobServe) with unified filtering and webhook integration.

## Overview

The multi-platform job scraper simultaneously searches multiple job boards, applies consistent filtering criteria, and delivers results via webhook integration. Perfect for automated job search workflows in n8n or similar automation platforms.

## Supported Platforms

- **LinkedIn** - Full-featured scraping with session-based authentication
- **JobServe** - Web scraping with full job description extraction
- **Indeed** (via jobspy) - Reliable scraping using python-jobspy library

### ✅ Indeed (via jobspy)

Indeed scraping uses the **python-jobspy** library which handles anti-bot measures automatically:

**Current Status:**
- ✅ Working reliably with python-jobspy
- ✅ Full job descriptions and metadata
- ✅ No 403 errors
- ✅ Support for multiple countries

**Requirements:**
```bash
pip install python-jobspy pandas
```

**Configuration:**
```json
{
  "platforms": ["indeed"]
}
```

**Features:**
- Built-in anti-bot handling
- Pandas DataFrame output
- Full job descriptions
- Salary information
- Posted dates
- Multiple countries supported (default: UK)

**Supported Countries:**
- `uk` - United Kingdom
- `us` - United States
- `ca` - Canada
- And more...

**Note:** python-jobspy uses sophisticated techniques to avoid detection, making it much more reliable than direct HTTP requests.

## Features

- 🔍 **Multi-Platform Search** - Search across multiple job boards simultaneously
- 🎯 **Unified Filtering** - Apply consistent filters across all platforms
- 📊 **Deduplication** - Automatically removes duplicate job listings
- 🚀 **Webhook Integration** - Send jobs one-by-one to n8n webhooks
- 💾 **Persistent Storage** - Track seen jobs to avoid duplicates
- 📈 **Progress Tracking** - Real-time feedback on scraping progress

## Installation

### Prerequisites

```bash
# Install Python dependencies
pip install -e .

# Install additional dependencies for multi-platform scraping
pip install beautifulsoup4 requests
```

### Configuration

Create a `multi_platform_config.json` file:

```json
{
  "linkedin_session_file": "session.json",
  "output_file": "multi_platform_jobs.json",
  "webhook_url": "https://n8n.your-domain.com/webhook/your-webhook-id",
  "searches": [
    {
      "keywords": "programme manager project manager",
      "location": "United Kingdom",
      "limit": 50,
      "platforms": ["linkedin", "jobserve"],
      "jobserve_url": "https://www.jobserve.com/gb/en/JobSearch.aspx?keywords=..."
    }
  ],
  "filters": {
    "max_posted_days_ago": 14,
    "employment_types": ["Contract", "Full-time", "Permanent"],
    "locations": ["United Kingdom", "UK", "Remote", "England"],
    "exclude_keywords": ["Internship", "Apprentice", "Entry Level"]
  }
}
```

### Configuration Fields

#### Global Settings

- `linkedin_session_file` - Path to LinkedIn session file (for authentication)
- `output_file` - JSON file to store results
- `webhook_url` - n8n webhook URL for job delivery

#### Search Configuration

Each search object defines a search query:

- `keywords` - Job search keywords
- `location` - Job location
- `limit` - Maximum jobs per platform
- `platforms` - Array of platforms to search (options: `linkedin`, `jobserve`)
- `jobserve_url` - Optional direct JobServe URL for specific searches

#### Filter Settings

- `max_posted_days_ago` - Maximum age of job posting (in days)
- `employment_types` - Array of acceptable employment types
- `locations` - Array of acceptable locations
- `exclude_keywords` - Keywords to exclude from results

## Usage

### Basic Usage

```bash
python multi_platform_job_scraper.py
```

### Run with Specific Configuration

```bash
python multi_platform_job_scraper.py --config custom_config.json
```

### Expected Output

```
============================================================
🤖 Multi-Platform Job Scraper
   LinkedIn + JobServe
============================================================

⚙️  Configuration:
   Platforms: linkedin, jobserve
   Searches: 1
   Employment types: ['Contract', 'Full-time', 'Permanent']
   Max posted days: 14
   Previously seen: 0 jobs

============================================================
🚀 Starting search cycle at 2026-01-30 21:30:00
============================================================

============================================================
📋 Search: programme manager in United Kingdom
============================================================

🔵 Searching LinkedIn: programme manager in United Kingdom
   Found 25 LinkedIn job URLs
   [1/25] Scraping LinkedIn job...
   ✅ Scraped 25 LinkedIn jobs

🟢 Searching JobServe: programme manager in United Kingdom
   Found 30 JobServe listings
   ✅ Scraped 28 JobServe jobs

📊 Total jobs found: 53
   Filtering...
   ✅ MATCH: Program Manager at Company A [LinkedIn]
   ✅ MATCH: Technical Program Manager at Company B [JobServe]
   ❌ Filtered: Junior Manager - Entry Level (excluded keyword)
   ...

💾 Saved 42 new jobs to multi_platform_jobs.json
   Total jobs in database: 42

📡 Sending 42 jobs to webhook ONE AT A TIME...
   Delay between sends: 2 seconds

[1/42] 📡 Sending job: Program Manager
   ✅ Webhook successful (status: 200)

...

✅ Successfully sent 42/42 jobs to webhook

============================================================
📊 FOUND 42 MATCHING JOBS
============================================================
   LinkedIn: 18 jobs
   JobServe: 24 jobs

============================================================
```

## Platform-Specific Details

### LinkedIn

LinkedIn requires authentication via session file:

1. **Create Session** (if you don't have one):
```bash
python samples/create_session.py
```

2. **Configure Session Path**:
```json
{
  "linkedin_session_file": "session.json"
}
```

3. **Session Security**:
- ⚠️ Never commit `session.json` to Git
- Add to `.gitignore`:
```
session.json
linkedin_session.json
multi_platform_jobs.json
```

### JobServe

JobServe scraping works without authentication:

- Extracts full job descriptions from detail pages
- Handles salary, location, and job type
- Includes posted date filtering
- Works with direct URLs or built search URLs

## Filtering System

### Date Filtering

Jobs are filtered based on posting date:

```json
{
  "filters": {
    "max_posted_days_ago": 14
  }
}
```

Supported formats:
- "2 hours ago"
- "3 days ago"
- "1 week ago"
- "1 month ago"

### Employment Type Filtering

```json
{
  "filters": {
    "employment_types": ["Contract", "Full-time", "Permanent"]
  }
}
```

Normalizes job types to match against filter.

### Location Filtering

```json
{
  "filters": {
    "locations": ["United Kingdom", "UK", "Remote"]
  }
}
```

Partial matches are supported (e.g., "London, UK" matches "UK").

### Keyword Exclusion

```json
{
  "filters": {
    "exclude_keywords": ["Internship", "Apprentice", "Entry Level"]
  }
}
```

Jobs with these keywords in the title are excluded.

## Webhook Integration

### Webhook Format

Each job is sent as a JSON payload:

```json
{
  "timestamp": "2026-01-30T21:30:00",
  "job_count": 1,
  "jobs": [
    {
      "job_title": "Program Manager",
      "company": "Example Company",
      "location": "London, UK",
      "employment_type": "Full-time",
      "salary": "£80,000 - £100,000",
      "posted_date": "2 days ago",
      "job_description": "Full job description here...",
      "linkedin_url": "https://linkedin.com/jobs/view/12345/",
      "source": "LinkedIn"
    }
  ]
}
```

### Webhook Delivery

Jobs are sent **one at a time** with configurable delays:

```python
# In multi_platform_job_scraper.py
send_jobs_to_webhook_one_by_one(jobs, webhook_url, delay_seconds=2)
```

Benefits:
- ✅ Reliability - Individual jobs won't fail the whole batch
- ✅ Rate limiting - Delays prevent webhook overload
- ✅ Traceability - Clear success/failure per job

## Data Storage

### Output Format

Results are stored in JSON format:

```json
{
  "last_updated": "2026-01-30T21:30:00",
  "total_jobs_found": 42,
  "jobs": [
    {
      "job_title": "Program Manager",
      "company": "Example Company",
      "location": "London, UK",
      "employment_type": "Full-time",
      "salary": "£80,000 - £100,000",
      "posted_date": "2 days ago",
      "job_description": "Full description...",
      "linkedin_url": "https://linkedin.com/jobs/view/12345/",
      "source": "LinkedIn"
    }
  ]
}
```

### Deduplication

- Tracks seen jobs by URL
- Prevents duplicate entries across runs
- Automatic removal of duplicates

## Advanced Usage

### Search Multiple Locations

```json
{
  "searches": [
    {
      "keywords": "programme manager",
      "location": "London",
      "limit": 25,
      "platforms": ["linkedin"]
    },
    {
      "keywords": "programme manager",
      "location": "Manchester",
      "limit": 25,
      "platforms": ["linkedin", "jobserve"]
    }
  ]
}
```

### Search Different Job Types

```json
{
  "searches": [
    {
      "keywords": "software engineer",
      "location": "United Kingdom",
      "limit": 50,
      "platforms": ["linkedin"]
    },
    {
      "keywords": "data scientist",
      "location": "United Kingdom",
      "limit": 50,
      "platforms": ["linkedin", "jobserve"]
    }
  ]
}
```

### Use Direct JobServe URL

For specific JobServe searches:

```json
{
  "searches": [
    {
      "keywords": "programme manager",
      "location": "London",
      "limit": 50,
      "platforms": ["jobserve"],
      "jobserve_url": "https://www.jobserve.com/gb/en/JobSearch.aspx?keywords=programme+manager&location=london"
    }
  ]
}
```

## Troubleshooting

### LinkedIn Session Expired

**Error**: `AuthenticationError: Not logged in to LinkedIn`

**Solution**:
```bash
python samples/create_session.py
```

### JobServe No Results

**Problem**: JobServe returns 0 jobs

**Solutions**:
1. Check if keywords match actual JobServe listings
2. Try a direct JobServe URL from browser
3. Verify JobServe selectors haven't changed
4. Check network connectivity

### Webhook Failures

**Problem**: Jobs not reaching n8n webhook

**Solutions**:
1. Verify webhook URL is correct
2. Check n8n webhook is active
3. Review webhook payload format
4. Check network connectivity to n8n

### Rate Limiting

**Problem**: LinkedIn or JobServe blocking requests

**Solutions**:
1. Increase delays between requests
2. Use slower scrape speeds
3. Rotate LinkedIn sessions if possible
4. Implement exponential backoff

## Examples

### Example Configuration - Contract Jobs Only

```json
{
  "linkedin_session_file": "session.json",
  "output_file": "contract_jobs.json",
  "webhook_url": "https://n8n.your-domain.com/webhook/contract-jobs",
  "searches": [
    {
      "keywords": "programme manager",
      "location": "United Kingdom",
      "limit": 50,
      "platforms": ["linkedin", "jobserve"]
    }
  ],
  "filters": {
    "employment_types": ["Contract"],
    "max_posted_days_ago": 7
  }
}
```

### Example Configuration - Senior Roles Only

```json
{
  "linkedin_session_file": "session.json",
  "output_file": "senior_jobs.json",
  "webhook_url": "https://n8n.your-domain.com/webhook/senior-jobs",
  "searches": [
    {
      "keywords": "senior programme manager",
      "location": "United Kingdom",
      "limit": 25,
      "platforms": ["linkedin"]
    },
    {
      "keywords": "head of programme",
      "location": "United Kingdom",
      "limit": 25,
      "platforms": ["linkedin", "jobserve"]
    }
  ],
  "filters": {
    "exclude_keywords": ["Junior", "Graduate", "Entry Level"],
    "max_posted_days_ago": 30
  }
}
```

## Best Practices

### 1. Session Management

- Keep LinkedIn sessions secure
- Regenerate sessions regularly
- Never commit session files
- Use environment variables for sensitive data

### 2. Rate Limiting

- Use appropriate delays between requests
- Respect platform rate limits
- Monitor for blocking issues

### 3. Error Handling

- Always handle exceptions gracefully
- Log errors for debugging
- Implement retry logic for transient failures

### 4. Data Quality

- Validate job data before sending
- Normalize employment types
- Clean up duplicate entries

### 5. Webhook Reliability

- Send jobs one at a time
- Implement retry logic
- Track successful/failed deliveries

## Integration with n8n

### n8n Workflow Setup

1. **Create Webhook Node** - Receive job data
2. **Add Function Node** - Process job data
3. **Add CV Generation** - Generate CV for each job
4. **Add Email/Notification** - Alert on new jobs

### Example n8n Workflow

```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.webhook",
      "webhookId": "your-webhook-id",
      "path": "webhook-path"
    },
    {
      "type": "n8n-nodes-base.function",
      "code": "// Process job data\nreturn items;"
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "method": "POST",
      "url": "https://your-cv-generator/api/generate"
    }
  ]
}
```

## Contributing

Contributions are welcome! Areas for improvement:

- Add more job boards (Indeed, Monster, etc.)
- Improve JobServe parsing
- Add more sophisticated filtering
- Implement machine learning for job matching
- Add database storage option

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and personal use. Make sure to comply with the Terms of Service of each job board. The authors are not responsible for any misuse of this tool.

## Support

For issues or questions:
1. Check this README
2. Review configuration examples
3. Check troubleshooting section
4. Open an issue on GitHub

## Links

- [GitHub Repository](https://github.com/ruskibeats/linkedin4N8N)
- [LinkedIn Scraper Docs](./INSTALL.md)
- [n8n Integration](./N8N-README.md)