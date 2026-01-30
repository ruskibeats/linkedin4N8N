# LinkedIn Scraper - Complete Installation Guide

Comprehensive guide for setting up and using the LinkedIn scraper with proper authentication.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [LinkedIn Authentication](#linkedin-authentication)
- [Running Your First Scrape](#running-your-first-scrape)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Prerequisites

### Required

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

### Recommended

- LinkedIn account (for authentication)

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/joeyism/linkedin_scraper.git
cd linkedin_scraper
```

### Step 2: Install Dependencies

```bash
pip install -e .
```

### Step 3: Install Playwright Browsers

```bash
playwright install chromium
```

**Note**: Playwright browsers are required for the scraper to work. Chromium is the most stable option.

### Step 4: Verify Installation

```bash
python -c "from linkedin_scraper import BrowserManager; print('✓ Installation successful')"
```

---

## LinkedIn Authentication

LinkedIn requires authentication to access profiles, jobs, and company data. You have two options:

### Option 1: Manual Login (Recommended for Most Users)

This is the easiest and most reliable method.

#### Step 1: Create Session File

Run the session creator script:

```bash
python samples/create_session.py
```

#### Step 2: Complete the Login in Browser

The script will:
1. Open a Chromium browser window
2. Navigate to https://www.linkedin.com/login
3. Wait for you to log in manually

**You must:**
- Enter your LinkedIn email and password
- Complete any 2FA verification (if enabled)
- Complete any CAPTCHA challenges
- Wait for your LinkedIn feed to load completely

#### Step 3: Session Saved

Once logged in, the script will automatically:
- Detect you're authenticated
- Save your session to `linkedin_session.json`
- Close the browser

**Output:**
```
============================================================
LinkedIn Session Creator
============================================================

This script will help you create a session file for LinkedIn.

Steps:
1. A browser window will open
2. Log in to LinkedIn manually
3. The script will detect when you're logged in
4. Your session will be saved to linkedin_session.json

============================================================

Opening LinkedIn login page...

🔐 Please log in to LinkedIn in the browser window...
   (You have 5 minutes to complete the login)

⏳ Waiting for login completion...

💾 Saving session to linkedin_session.json...

============================================================
✅ Success! Session file created.
============================================================

Session saved to: linkedin_session.json
```

#### Step 4: Protect Your Session File

⚠️ **IMPORTANT**: The `linkedin_session.json` file contains your authentication cookies and session data.

**DO:**
- Keep it in your project directory
- Use it for scraping
- Regenerate it if session expires

**DO NOT:**
- Commit it to Git or any public repository
- Share it with anyone
- Upload it to cloud storage

**Add to `.gitignore`:**
```bash
echo "linkedin_session.json" >> .gitignore
echo "session.json" >> .gitignore
```

### Option 2: Programmatic Login

For automation scenarios, you can use credentials:

#### Step 1: Set Environment Variables

```bash
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
```

#### Step 2: Create Session Programmatically

```python
import asyncio
import os
from linkedin_scraper import BrowserManager, login_with_credentials

async def create_session():
    async with BrowserManager(headless=False) as browser:
        await browser.page.goto("https://www.linkedin.com/login")
        
        await login_with_credentials(
            browser.page,
            username=os.getenv("LINKEDIN_EMAIL"),
            password=os.getenv("LINKED_PASSWORD")
        )
        
        await browser.save_session("linkedin_session.json")
        print("✅ Session saved!")

asyncio.run(create_session())
```

⚠️ **Warning**: LinkedIn may block programmatic logins. Manual login is more reliable.

### Option 3: Extract Cookies from Browser (Advanced)

If you prefer to use your existing browser session:

#### Firefox:
1. Log into LinkedIn in Firefox
2. Install "Cookie-Editor" extension
3. Click the extension icon
4. Select "Export Cookies"
5. Export as JSON
6. Save as `linkedin_session.json`

#### Chrome:
1. Log into LinkedIn in Chrome
2. Install "EditThisCookie" extension
3. Click the extension icon
4. Select "Export All Cookies"
5. Export as JSON
6. Save as `linkedin_session.json`

---

## Running Your First Scrape

### Option 1: Using the Session File

```python
import asyncio
from linkedin_scraper import BrowserManager, PersonScraper

async def main():
    async with BrowserManager(headless=False) as browser:
        # Load your authenticated session
        await browser.load_session("linkedin_session.json")
        
        # Create scraper
        scraper = PersonScraper(browser.page)
        
        # Scrape a profile
        person = await scraper.scrape("https://www.linkedin.com/in/williamhgates/")
        
        # Print results
        print(f"Name: {person.name}")
        print(f"Headline: {person.headline}")
        print(f"Location: {person.location}")
        print(f"Skills: {', '.join(person.skills[:5])}")

asyncio.run(main())
```

### Option 2: Job Search Example

```python
import asyncio
from linkedin_scraper import BrowserManager, JobSearchScraper

async def main():
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = JobSearchScraper(browser.page)
        jobs = await scraper.search(
            keywords="Python Developer",
            location="San Francisco",
            limit=5
        )
        
        print(f"Found {len(jobs)} jobs:")
        for job in jobs:
            print(f"  • {job.title} at {job.company}")

asyncio.run(main())
```

### Option 3: Company Scraper Example

```python
import asyncio
from linkedin_scraper import BrowserManager, CompanyScraper

async def main():
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = CompanyScraper(browser.page)
        company = await scraper.scrape("https://www.linkedin.com/company/microsoft/")
        
        print(f"Company: {company.name}")
        print(f"Industry: {company.industry}")
        print(f"Employees: {company.company_size}")

asyncio.run(main())
```

---

## Configuration

### Environment Variables

You can configure the scraper using environment variables:

```bash
# Browser settings
export LINKEDIN_HEADLESS=true           # Run in headless mode
export LINKEDIN_SLOW_MO=100              # Slow down operations (ms)

# Session settings
export LINKEDIN_SESSION_FILE="linkedin_session.json"
```

### Session File Locations

The scraper looks for session files in this order:

1. `linkedin_session.json` (current directory)
2. `session.json` (current directory)
3. `~/.linkedin_scraper/session.json` (home directory)

### Browser Options

```python
from linkedin_scraper import BrowserManager

browser = BrowserManager(
    headless=False,              # Show browser (useful for debugging)
    slow_mo=100,                # Slow down (helps with rate limiting)
    viewport={"width": 1920, "height": 1080},  # Browser window size
    user_agent="Custom User Agent String"  # Override user agent
)
```

---

## Examples

### Example 1: Scrape Person Profile

Save as `scrape_profile.py`:

```python
#!/usr/bin/env python3
import asyncio
import sys
from linkedin_scraper import BrowserManager, PersonScraper

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_profile.py <linkedin_profile_url>")
        sys.exit(1)
    
    profile_url = sys.argv[1]
    
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = PersonScraper(browser.page)
        person = await scraper.scrape(profile_url)
        
        # Print full profile
        print("="*60)
        print(f"Profile: {person.name}")
        print("="*60)
        print(f"Headline: {person.headline}")
        print(f"Location: {person.location}")
        print(f"About: {person.about[:200]}...")
        print()
        print(f"Experience: {len(person.experiences)} roles")
        print(f"Education: {len(person.educations)} schools")
        print(f"Skills: {len(person.skills)} skills")
        print()

asyncio.run(main())
```

**Run:**
```bash
python scrape_profile.py "https://www.linkedin.com/in/someone/"
```

### Example 2: Search Jobs

Save as `search_jobs.py`:

```python
#!/usr/bin/env python3
import asyncio
from linkedin_scraper import BrowserManager, JobSearchScraper

async def main():
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = JobSearchScraper(browser.page)
        
        # Search for jobs
        jobs = await scraper.search(
            keywords="Program Manager",
            location="London",
            limit=10
        )
        
        print(f"Found {len(jobs)} jobs:\n")
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Link: {job.linkedin_url}")
            print()

asyncio.run(main())
```

**Run:**
```bash
python search_jobs.py
```

### Example 3: Scrape Company Posts

Save as `scrape_posts.py`:

```python
#!/usr/bin/env python3
import asyncio
from linkedin_scraper import BrowserManager, CompanyPostsScraper

async def main():
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = CompanyPostsScraper(browser.page)
        
        # Scrape company posts
        posts = await scraper.scrape(
            "https://www.linkedin.com/company/microsoft/",
            limit=5
        )
        
        print(f"Found {len(posts)} posts:\n")
        
        for i, post in enumerate(posts, 1):
            print(f"{i}. {post.posted_date}")
            print(f"   {post.text[:100]}...")
            print(f"   Reactions: {post.reactions_count}")
            print(f"   Comments: {post.comments_count}")
            print()

asyncio.run(main())
```

**Run:**
```bash
python scrape_posts.py
```

---

## Troubleshooting

### Common Issues

#### 1. Session File Not Found

**Error:**
```
FileNotFoundError: session.json not found
```

**Solution:**
```bash
# Create session file
python samples/create_session.py
```

#### 2. Authentication Failed

**Error:**
```
AuthenticationError: Not logged in to LinkedIn
```

**Solution:**
```bash
# Recreate session file
rm -f linkedin_session.json
python samples/create_session.py
```

#### 3. Rate Limited

**Error:**
```
RateLimitError: LinkedIn rate limit reached
```

**Solution:**
- Add delays between requests
- Use `slow_mo` option to slow down scraping
- Wait 5-10 seconds between operations

```python
import asyncio
await asyncio.sleep(5)  # Wait 5 seconds
```

#### 4. Playwright Not Found

**Error:**
```
ModuleNotFoundError: No module named 'playwright'
```

**Solution:**
```bash
# Install Playwright
pip install playwright
playwright install chromium
```

#### 5. Browser Timeout

**Error:**
```
TimeoutError: Page load timeout
```

**Solution:**
```python
# Increase timeout
browser = BrowserManager(
    headless=False,
    timeout=60000  # 60 seconds
)
```

#### 6. Profile Not Found or Private

**Error:**
```
ProfileNotFoundError: Profile not found or private
```

**Solution:**
- Check the profile URL is correct
- Verify you're logged into the correct account
- Some profiles may only be visible to 1st degree connections
- The profile may be private (not visible to your network)

### Debugging Mode

For debugging, run in non-headless mode:

```python
async with BrowserManager(headless=False) as browser:
    # Watch the browser do its work
    await browser.load_session("linkedin_session.json")
    scraper = PersonScraper(browser.page)
    person = await scraper.scrape("https://linkedin.com/in/someone/")
```

This opens a visible browser window so you can see what's happening.

---

## Best Practices

### 1. Rate Limiting

Always add delays between requests to avoid being blocked:

```python
import asyncio

# Delay between individual scrapes
await asyncio.sleep(2)

# Delay between pages
await asyncio.sleep(5)
```

### 2. Session Management

- **Reuse sessions** - Don't create a new session for each run
- **Rotate sessions** - Create multiple sessions and rotate between them
- **Backup sessions** - Keep a backup of your session file

### 3. Error Handling

Always handle exceptions properly:

```python
from linkedin_scraper import (
    AuthenticationError,
    RateLimitError,
    ProfileNotFoundError
)

try:
    person = await scraper.scrape(url)
except AuthenticationError:
    print("Not logged in - session expired")
except RateLimitError:
    print("Rate limited by LinkedIn")
except ProfileNotFoundError:
    print("Profile not found or private")
```

### 4. Security

- Never commit session files to Git
- Use `.gitignore` to protect session files
- Rotate credentials regularly
- Use environment variables for sensitive data

### 5. Testing

- Test with headless=False during development
- Use headless=True in production
- Start with small datasets before scaling up
- Monitor for rate limiting issues

---

## Advanced Features

### Progress Callbacks

Track scraping progress with callbacks:

```python
from linkedin_scraper import ConsoleCallback, PersonScraper

async def scrape_with_progress():
    callback = ConsoleCallback()  # Prints progress to console
    
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = PersonScraper(browser.page, callback=callback)
        person = await scraper.scrape("https://www.linkedin.com/in/someone/")

asyncio.run(scrape_with_progress())
```

### Custom Callbacks

```python
from linkedin_scraper import ProgressCallback

class MyCallback(ProgressCallback):
    async def on_start(self, scraper_type: str, url: str):
        print(f"Starting {scraper_type} scraping: {url}")
    
    async def on_progress(self, message: str, percent: int):
        print(f"[{percent}%] {message}")
    
    async def on_complete(self, scraper_type: str, url: str):
        print(f"Completed {scraper_type}: {url}")
    
    async def on_error(self, error: Exception):
        print(f"Error: {error}")
```

### Job Search with Pagination

```python
from linkedin_scraper import BrowserManager, JobSearchScraper

async def search_multiple_pages():
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("linkedin_session.json")
        
        scraper = JobSearchScraper(browser.page)
        
        # Search for jobs across multiple pages
        jobs = await scraper.search(
            keywords="Software Engineer",
            location="United States",
            limit=100,      # Get up to 100 jobs
            max_pages=5     # Check up to 5 pages
        )
        
        print(f"Found {len(jobs)} jobs across multiple pages")

asyncio.run(search_multiple_pages())
```

---

## Support

### Documentation

- [Full Documentation](https://github.com/joeyism/linkedin_scraper)
- [API Reference](https://github.com/joeyism/linkedin_scraper)
- [Examples Directory](https://github.com/joeyism/linkedin_scraper/tree/master/samples)

### Issues & Bugs

- [Issue Tracker](https://github.com/joeyboundin/linkedin_scraper/issues)
- [Troubleshooting Guide](https://github.com/joeyism/linkedin_scraper/wiki/Troubleshooting)

### Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/joeyism/linkedin_scraper/blob/main/CONTRIBUTING.md) for guidelines.

---

## License

Apache License 2.0 - see [LICENSE](https://github.com/joeyism/linkedin_scraper/blob/main/LICENSE)

---

## Disclaimer

This tool is for educational purposes only. Make sure to comply with LinkedIn's Terms of Service and use responsibly. The authors are not responsible for any misuse of this tool.