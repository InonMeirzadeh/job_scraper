from datetime import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2
import schedule
import time
import smtplib
from email.mime.text import MIMEText
import logging
import json
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_valid_job(title, location):
    """
    Checks if the job is a junior position in Israel.
    """
    return 'junior' in title.lower() and 'israel' in location.lower()


def scrape_comeet_jobs(url, company_name):
    retries = 3
    while retries > 0:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                break
            else:
                logging.warning(f"Failed to retrieve page for {company_name}. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching the page for {company_name}: {e}")
        retries -= 1
        time.sleep(3)

    if retries == 0:
        logging.error(f"Failed to retrieve page for {company_name} after retries.")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    jobs = []

    # Try to find job data in any script tag
    script_tags = soup.find_all('script')
    job_data = None
    for script in script_tags:
        if script.string and 'gnewtonJobsJson' in script.string:
            match = re.search(r'gnewtonJobsJson\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
            if match:
                try:
                    job_data = json.loads(match.group(1))
                    break
                except json.JSONDecodeError:
                    continue

    if job_data:
        logging.info(f"Found {len(job_data)} job listings for {company_name}")
        for job in job_data:
            title = job.get('title', '')
            location = job.get('location', '')
            description = job.get('description', '')
            job_url = f"{url.rstrip('/')}/jobs/{job.get('id')}"

            logging.info(f"Processing job: {title} in {location}")
            if is_valid_job(title, location):
                logging.info(f"Valid junior job found: {title}")
                jobs.append({
                    'company': company_name,
                    'title': title,
                    'location': location,
                    'description': description,
                    'link': job_url
                })
            else:
                logging.info(f"Job doesn't meet criteria: {title}")
    else:
        logging.error(f"Could not find job data for {company_name}")

    logging.info(f"Found {len(jobs)} valid junior jobs for {company_name}")
    return jobs


def store_jobs_in_database(jobs):
    """
    Stores the scraped job postings in a PostgreSQL database.
    """
    conn = psycopg2.connect(
        dbname='job_scraper',
        user='postgres',
        password='*******',
        host='localhost',
        port='5432'
    )
    cursor = conn.cursor()
    for job in jobs:
        cursor.execute("""
            INSERT INTO jobs (company, title, location, description, link, date_posted)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            job['company'], job['title'], job['location'], job['description'], job['link'], datetime.now()
        ))
    conn.commit()
    cursor.close()
    conn.close()
    logging.info(f"Stored {len(jobs)} jobs in the database")


def send_email_notification(jobs):
    """
    Sends an email notification with the new job postings.
    """
    if not jobs:
        logging.info("No new jobs to send email about")
        return

    sender = "inon164@gmail.com"
    receiver = "inon164@gmail.com"
    subject = "New Junior Job Postings in Israel"
    body = "Here are the new junior job postings in Israel:\n\n"
    for job in jobs:
        body += f"Company: {job['company']}\nTitle: {job['title']}\nLocation: {job['location']}\nDescription:" \
                f" {job['description']}\nLink: {job['link']}\n\n"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, "*****")
            server.send_message(msg)
        logging.info(f"Email sent with {len(jobs)} job listings")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def job_scraping_task():
    companies = {
        "inmanage": "https://www.comeet.com/jobs/inmanage/B7.006",
        # Add more companies using Comeet template here
    }

    all_jobs = []
    for company, url in companies.items():
        logging.info(f"Scraping jobs for {company}...")
        jobs = scrape_comeet_jobs(url, company)
        all_jobs.extend(jobs)

    if all_jobs:
        store_jobs_in_database(all_jobs)
        send_email_notification(all_jobs)
    else:
        logging.info("No new junior jobs found in Israel")


def main():
    job_scraping_task()
    schedule.every(1).minutes.do(job_scraping_task)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()