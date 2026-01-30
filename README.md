# LinkedIn Scraper

[![PyPI version](https://badge.fury.io/py/linkedin-scraper.svg)](https://badge.fury.io/py/linkedin-scraper)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Async LinkedIn scraper built with Playwright for extracting profile, company, and job data from LinkedIn.

## ⚠️ Breaking Changes in v3.0.0

**Version 3.0.0 introduces breaking changes and is NOT backwards compatible with previous versions.**

### What Changed:
- **Playwright instead of Selenium** - Complete rewrite using Playwright for better performance and reliability
- **Async/await throughout** - All methods are now async and require `await`
- **New package structure** - Imports have changed (e.g., `from linkedin_scraper import PersonScraper`)
- **Updated data models** - Using Pydantic models instead of simple objects
- **Different API** - Method signatures and return types have changed

### Migration Guide:

**Before (v2.x with Selenium):**
```python
from linkedin_scraper import Person

person = Person("https://linkedin.com/in/username", driver=driver)
print(person.name)
```

**After (v3.0+ with Playwright):**
```python
import asyncio
from linkedin_scraper import BrowserManager, PersonScraper

async def main():
    async with BrowserManager() as browser:
        await browser.load_session("session.json")
        scraper = PersonScraper(browser.page)
        person = await scraper.scrape("https://linkedin.com/in/username")
        print(person.name)

asyncio.run(main())
```

**If you need the old Selenium-based version:**
```bash
pip install linkedin-scraper==2.11.2
```
## Quick Testing

To test that this works, you can clone this repo, install dependencies with
```
git clone https://github.com/joeyism/linkedin_scraper.git
cd linkedin_scraper
pip3 install -e .
```
then run
```
python3 samples/create_session.py
python3 samples/scrape_company.py
python3 samples/scrape_person.py
```
and you will see the scraping in action.

---

## Features

- **Person Profiles** - Scrape comprehensive profile information
  - Basic info (name, headline, location, about)
  - Work experience with details
  - Education history
  - Skills and accomplishments
  
- **Company Pages** - Extract company information
  - Company overview and details
  - Industry and size
  - Headquarters location
  
- **Company Posts** - Scrape posts from company pages
  - Post content and text
  - Reactions, comments, reposts counts
  - Posted date and images
  
- **Job Listings** - Scrape job postings
  - Job details and requirements
  - Company information
  - Application links

- **Async/Await** - Modern async Python with Playwright
- **Type Safety** - Full Pydantic models for all data
- **Progress Callbacks** - Track scraping progress
- **Session Management** - Reuse authenticated sessions

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/joyism/linkedin_scraper.git
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

### Step 4: Verify Installation

```bash
python -c "from linkedin_scraper import BrowserManager; print('✓ Installation successful')"
```

## Quick Start

### Basic Usage

```python
import asyncio
from linkedin_scraper import BrowserManager, PersonScraper

async def main():
    # Initialize browser
    async with BrowserManager(headless=False) as browser:
        # Load authenticated session
        await browser.load_session("session.json")
        
        # Create scraper
        scraper = PersonScraper(browser.page)
        
        # Scrape a profile
        person = await scraper.scrape("https://linkedin.com/in/williamhgates/")
        
        # Access data
        print(f"Name: {person.name}")
        print(f"Headline: {person.headline}")
        print(f"Location: {person.location}")
        print(f"Experiences: {len(person.experiences)}")
        print(f"Education: {len(person.educations)}")

asyncio.run(main())
```

### Company Scraping

```python
from linkedin_scraper import CompanyScraper

async def scrape_company():
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("session.json")
        
        scraper = CompanyScraper(browser.page)
        company = await scraper.scrape("https://linkedin.com/company/microsoft/")
        
        print(f"Company: {company.name}")
        print(f"Industry: {company.industry}")
        print(f"Size: {company.company_size}")
        print(f"About: {company.about_us[:200]}...")

asyncio.run(scrape_company())
```

### Job Scraping

```python
from linkedin_scraper import JobSearchScraper

async def search_jobs():
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("session.json")
        
        scraper = JobSearchScraper(browser.page)
        jobs = await scraper.search(
            keywords="Python Developer",
            location="San Francisco",
            limit=10
        )
        
        for job in jobs:
            print(f"{job.title} at {job.company}")
            print(f"Location: {job.location}")
            print(f"Link: {job.linkedin_url}")
            print("---")

asyncio.run(search_jobs())
```

### Company Posts Scraping

```python
from linkedin_scraper import BrowserManager, CompanyPostsScraper

async def scrape_company_posts():
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("session.json")
        
        scraper = CompanyPostsScraper(browser.page)
        posts = await scraper.scrape(
            "https://linkedin.com/company/microsoft/",
            limit=10
        )
        
        for post in posts:
            print(f"Posted: {post.posted_date}")
            print(f"Text: {post.text[:200]}...")
            print(f"Reactions: {post.reactions_count}")
            print(f"Comments: {post.comments_count}")
            print(f"URL: {post.linkedin_url}")
            print("---")

asyncio.run(scrape_company_posts())
```

## Authentication

LinkedIn requires authentication to access profiles, jobs, and company data. You need to create a session file with your LinkedIn cookies/credentials.

### Method 1: Manual Login (RECOMMENDED - Most Reliable)

This is the easiest and most reliable method for most users.

#### Step 1: Run the Session Creator

```bash
python samples/create_session.py
```

#### Step 2: Complete Login in Browser

The script will open a Chromium browser window and navigate to LinkedIn login.

**You must:**
- Enter your LinkedIn email and password
- Complete any 2FA verification (if enabled)
- Solve any CAPTCHA challenges if present
- **Wait until your LinkedIn feed loads completely** - this is critical!
- Keep the browser window open until you see the session is saved

#### Step 3: Session Saved

Once the script detects you're logged in, it will automatically save your session to `linkedin_session.json` and close the browser.

**Expected Output:**
```
LinkedIn Session Creator

This script will help you create a session file for LinkedIn.

Steps:
1. A browser window will open
2. Log in to LinkedIn manually
3. The script will detect when you're logged in
4. Your session will be saved to linkedin_session.json


Opening LinkedIn login page...

🔐 Please log in to LinkedIn in the browser window...
   (You have 5 minutes to complete the login)

⏳ Waiting for login completion...

💾 Saving session to linkedin_session.json...

✅ Success! Session file created.

Session saved to: linkedin_session.json
```

#### Step 4: Protect Your Session File

⚠️ **CRITICAL SECURITY WARNING**: 
The `linkedin_session.json` file contains your authentication cookies and session tokens.

**DO:**
- ✅ Keep it in your project directory
- ✅ Use it for all scraping operations
- ✅ Regenerate it when session expires (typically every few days)

**DO NOT:**
- ❌ Commit it to Git or any public repository
- ❌ Share it with anyone
- ❌ Upload it to cloud storage
- ❌ Post it publicly anywhere

**Add to .gitignore:**
```bash
# Protect session files from accidental commits
echo "linkedin_session.json" >> .gitignore
echo "session.json" >> .gitignore
```

#### Troubleshooting Manual Login

**Problem: Script doesn't detect login completion**

**Solutions:**
- Make sure you actually logged in (check if you see your feed)
- Wait for your LinkedIn feed to load completely
- Verify the browser didn't close unexpectedly
- Check for CAPTCHA or 2FA that might be blocking

**Problem: Session file not created**

**Solutions:**
- Run the script again with `python samples/create_session.py`
- Check if you have write permissions in the current directory
- Ensure you're logged into the correct LinkedIn account

**Problem: Session expired too quickly**

**Solutions:**
- Regenerate the session file with `python samples/create_session.py`
- Sessions typically last several days but can expire if:
  - Your LinkedIn session times out
  - You logged out elsewhere
  - LinkedIn rotated session tokens

---

### Method 2: Programmatic Login (For Automation)

For CI/CD or automated workflows, you can use credentials instead.

#### Step 1: Set Environment Variables

```bash
# Linux/Mac
export LINKEDIN_EMAIL="your.email@example.com"
export LINKEDIN_PASSWORD="your_password_here"

# Windows
set LINKEDIN_EMAIL=your.email@example.com
set LINKEDIN_PASSWORD=your_password_here
```

#### Step 2: Create Session Programmatically

```python
import asyncio
import os
from linkedin_scraper import BrowserManager, login_with_credentials

async def create_session():
    async with BrowserManager(headless=False) as browser:
        # Navigate to LinkedIn
        await browser.page.goto("https://www.linkedin.com/login")
        
        # Login programmatically
        await login_with_credentials(
            browser.page,
            username=os.getenv("LINKEDIN_EMAIL"),
            password=os.getenv("LINKEDIN_PASSWORD")
        )
        
        # Save session for reuse
        await browser.save_session("linkedin_session.json")
        print("✅ Session saved programmatically!")

asyncio.run(create_session())
```

⚠️ **Warning**: LinkedIn may detect and block programmatic logins. Manual login is more reliable for most users. LinkedIn has sophisticated anti-bot measures.

---

### Method 3: Export Cookies from Browser (Advanced)

If you already have an active LinkedIn session in your browser, you can extract the cookies.

#### Firefox:
1. Log into LinkedIn in Firefox
2. Install "Cookie-Editor" extension (or similar cookie export tool)
3. Click the extension icon → "Export Cookies"
4. Select all LinkedIn cookies
5. Export as JSON format
6. Save as `linkedin_session.json` in your project directory

#### Chrome:
1. Log into LinkedIn in Chrome
2. Install "EditThisCookie" extension (or similar cookie export tool)
3. Click the extension icon → "Export All Cookies"
4. Select all LinkedIn cookies
5. Export as JSON format
6. Save as `linkedin_session.json` in your project directory

⚠️ **Important**: Make sure you export ALL LinkedIn cookies, not just authentication cookies. The scraper needs all LinkedIn cookies to work properly.

---

### Session File Locations

The scraper searches for session files in this order:

1. `linkedin_session.json` (current directory)
2. `session.json` (current directory)
3. `~/.linkedin_scraper/session.json` (home directory)

You can specify a custom location:

```python
async with BrowserManager() as browser:
    await browser.load_session("/path/to/your/session.json")
    # ... rest of your scraping code
```

Or set an environment variable:

```bash
export LINKEDIN_SESSION_FILE="/path/to/your/session.json"
```

## Progress Tracking

Track scraping progress with callbacks:

```python
from linkedin_scraper import ConsoleCallback, PersonScraper

async def scrape_with_progress():
    callback = ConsoleCallback()  # Prints progress to console
    
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("session.json")
        
        scraper = PersonScraper(browser.page, callback=callback)
        person = await scraper.scrape("https://linkedin.com/in/williamhgates/")

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

## Data Models

All scraped data is returned as Pydantic models:

### Person

```python
class Person(BaseModel):
    name: str
    headline: Optional[str]
    location: Optional[str]
    about: Optional[str]
    linkedin_url: str
    experiences: List[Experience]
    educations: List[Education]
    skills: List[str]
    accomplishments: Optional[Accomplishment]
```

### Company

```python
class Company(BaseModel):
    name: str
    industry: Optional[str]
    company_size: Optional[str]
    headquarters: Optional[str]
    founded: Optional[str]
    specialties: List[str]
    about: Optional[str]
    linkedin_url: str
```

### Job

```python
class Job(BaseModel):
    title: str
    company: str
    location: Optional[str]
    description: Optional[str]
    employment_type: Optional[str]
    seniority_level: Optional[str]
    linkedin_url: str
```

### Post

```python
class Post(BaseModel):
    linkedin_url: Optional[str]
    urn: Optional[str]
    text: Optional[str]
    posted_date: Optional[str]
    reactions_count: Optional[int]
    comments_count: Optional[int]
    reposts_count: Optional[int]
    image_urls: List[str]
```

## Advanced Usage

### Browser Configuration

```python
browser = BrowserManager(
    headless=False,  # Show browser window
    slow_mo=100,     # Slow down operations (ms)
    viewport={"width": 1920, "height": 1080},
    user_agent="Custom User Agent"
)
```

### Error Handling

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

## Best Practices

1. **Rate Limiting** - Add delays between requests
   ```python
   import asyncio
   await asyncio.sleep(2)  # 2 second delay
   ```

2. **Session Reuse** - Save and reuse sessions to avoid frequent logins

3. **Error Handling** - Always handle exceptions (rate limits, auth errors, etc.)

4. **Headless Mode** - Use `headless=False` during development, `True` for production

5. **Respect LinkedIn** - Don't scrape aggressively, respect rate limits

## Requirements

- Python 3.8+
- Playwright
- Pydantic 2.0+
- aiofiles
- python-dotenv (optional, for credentials)

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational purposes only. Make sure to comply with LinkedIn's Terms of Service and use responsibly. The authors are not responsible for any misuse of this tool.

## Links

- [GitHub Repository](https://github.com/joeyism/linkedin_scraper)
- [Issue Tracker](https://github.com/joeyism/linkedin_scraper/issues)
- [PyPI Package](https://pypi.org/project/linkedin-scraper/)
