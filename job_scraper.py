import re
import time
import logging
from bs4 import BeautifulSoup
from config.config import COMPANIES
from utils.browser_config import initialize_webdriver
from utils.database_utils import store_new_jobs
from utils.email_utils import send_email
from config.keywords_config import JUNIOR_KEYWORDS, LOCATION_KEYWORDS
from utils.scheduler_config import configure_scheduler
from config.logging_config import configure_logging

# Set up logging
configure_logging()


def is_valid_job(title, location, experience_level):
    """
    Determines if the job is a junior position in Israel based on title and location.
    """
    title_lower = title.lower()
    location_lower = location.lower()

    is_junior = any(keyword in title_lower for keyword in JUNIOR_KEYWORDS) or experience_level == 'Entry-level'
    is_in_israel = any(keyword in location_lower for keyword in LOCATION_KEYWORDS)

    if not is_junior:
        logging.debug(f"Skipping job not matching junior criteria: {title}")
    if not is_in_israel:
        logging.debug(f"Skipping job not matching Israel location criteria: {location}")

    return is_junior and is_in_israel


def scrape_comeet_jobs(url, company_name):
    """
    Scrapes job listings from a Comeet jobs page for a given company.
    """
    driver = initialize_webdriver()
    jobs = []

    try:
        logging.info(f"Scraping jobs for {company_name}...")
        driver.get(url)
        time.sleep(5)  # Allow time for JavaScript to execute
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_listings = soup.find_all('a', class_='positionItem')

        logging.info(f"Found {len(job_listings)} potential jobs for {company_name}")

        for job in job_listings:
            title = job.find('span', class_='positionLink').get_text(strip=True) if job.find('span',
                                                                                             class_='positionLink') else ''
            link = job['href'] if job.has_attr('href') else ''
            parent = job.find_parent()
            location = parent.find('i', class_='fa fa-map-marker').find_next_sibling(
                string=True).strip() if parent.find('i', class_='fa fa-map-marker') else ''
            experience = parent.find(string=re.compile(r'\b(Entry-level|Mid-level|Senior)\b')).strip() if parent.find(
                string=re.compile(r'\b(Entry-level|Mid-level|Senior)\b')) else 'Not specified'

            if is_valid_job(title, location, experience):
                jobs.append({
                    'company': company_name,
                    'title': title,
                    'location': location,
                    'experience_level': experience,
                    'link': link
                })

    finally:
        driver.quit()

    return jobs


def main_task():
    """
    Main task to scrape jobs, store them in the database, and send email notifications.
    """
    all_jobs = []
    for company, url in COMPANIES.items():
        all_jobs.extend(scrape_comeet_jobs(url, company))

    if all_jobs:
        new_jobs = store_new_jobs(all_jobs)
        send_email(new_jobs)
    else:
        logging.info("No jobs found")


def main():
    configure_scheduler(main_task, 50)


if __name__ == "__main__":
    main()
