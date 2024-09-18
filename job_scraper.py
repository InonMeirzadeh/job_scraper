import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import psycopg2
import schedule
import time
import smtplib
from email.mime.text import MIMEText
import logging
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_valid_job(title, location):
    """
    Checks if the job is a junior position in Israel.
    """
    # Define keywords to capture junior-level positions
    junior_keywords = ['junior', 'entry-level', 'associate', 'graduate', 'מתחיל', 'זוטר']
    # Define keywords for locations in Israel
    location_keywords = ['israel', 'tel aviv', 'jerusalem', 'haifa', 'bnei brak', 'champion tower', 'שששת הימים',
                         'רמת גן', 'הרצליה']

    # Convert title and location to lowercase for case-insensitive matching
    title_lower = title.lower()
    location_lower = location.lower()

    # Check if any of the junior keywords and location keywords are present
    is_junior = any(keyword in title_lower for keyword in junior_keywords)
    is_in_israel = any(keyword in location_lower for keyword in location_keywords)

    return is_junior and is_in_israel


def scrape_comeet_jobs(url, company_name):
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        logging.info(f"Loading page for {company_name}...")
        driver.get(url)
        time.sleep(5)  # Allow time for JavaScript to execute

        # Get the page source after loading
        page_source = driver.page_source

        # Use BeautifulSoup to parse the page content
        soup = BeautifulSoup(page_source, 'html.parser')

        jobs = []

        # Find job listings by searching for anchors with job links
        job_listings = soup.find_all('a', href=True, class_=re.compile(r'positionItem|job|listing|positionLink|ng-if', re.I))

        logging.info(f"Found {len(job_listings)} potential job listings in the page for {company_name}")

        for job in job_listings:
            # Extract job title from the anchor or its children
            title_element = job.find('span', class_=re.compile(r'positionItem|positionLink|title|jobTitle|ng-if', re.I)) or job.find('h2')
            title_text = title_element.get_text(strip=True) if title_element else 'Unknown Title'

            # Extract job link
            job_link = job['href'] if job.has_attr('href') else ''

            # Find the parent or nearby container to extract job details
            parent = job.find_parent()

            # Extract job location by looking for location elements
            location_element = parent.find('i', class_=re.compile(r'fa-map-marker|location', re.I)) or parent.find(
                string=re.compile(r'(Location|Tel Aviv|Israel|Jerusalem|Haifa)', re.I))
            location_text = location_element.find_next_sibling(
                text=True).strip() if location_element else 'Unknown Location'

            # Extract experience level by looking for relevant text
            experience_element = parent.find(string=re.compile(r'\b(Entry-level|Junior|Mid-level|Senior|מתחיל|זוטר)\b'))
            experience_level = experience_element.strip() if experience_element else 'Unknown Experience'

            # Extract employment type (Full-time/Part-time)
            employment_type_element = parent.find(
                string=re.compile(r'\b(Full-time|Part-time|Contract|משרה מלאה|משרה חלקית)\b'))
            employment_type = employment_type_element.strip() if employment_type_element else 'Unknown Employment Type'

            logging.info(f"Processing job: {title_text} in {location_text} with experience level {experience_level}")

            # Only add jobs that meet the junior position and location criteria
            if is_valid_job(title_text, location_text):
                logging.info(f"Valid junior job found: {title_text}")
                jobs.append({
                    'company': company_name,
                    'title': title_text,
                    'location': location_text,
                    'experience_level': experience_level,
                    'employment_type': employment_type,
                    'description': '',  # Add description extraction logic if available
                    'link': job_link
                })

        if jobs:
            logging.info(f"Found {len(jobs)} valid junior jobs for {company_name}")
        else:
            logging.error(f"No valid job data found for {company_name}")

        return jobs

    finally:
        driver.quit()


def store_jobs_in_database(jobs):
    """
    Stores the scraped job postings in a PostgreSQL database, only if they don't already exist.
    """
    conn = psycopg2.connect(
        dbname='job_scraper',
        user='postgres',
        password='INon16meir!',  # Replace with your actual password
        host='localhost',
        port='5432'
    )
    cursor = conn.cursor()

    new_jobs = []

    for job in jobs:
        # Check if the job already exists in the database
        cursor.execute("""
            SELECT id FROM jobs WHERE company = %s AND title = %s AND location = %s
        """, (job['company'], job['title'], job['location']))
        result = cursor.fetchone()

        if not result:  # If no result, the job is new
            cursor.execute("""
                INSERT INTO jobs (company, title, location, description, link, date_posted)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                job['company'], job['title'], job['location'], job['description'], job['link'], datetime.now()
            ))
            new_jobs.append(job)

    conn.commit()
    cursor.close()
    conn.close()

    logging.info(f"Stored {len(new_jobs)} new jobs in the database")

    return new_jobs  # Return only the new jobs


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
        body += f"Company: {job['company']}\nTitle: {job['title']}\nLocation: {job['location']}\nDescription: {job['description']}\nLink: {job['link']}\n\n"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, "lrda hqrz qzax blkf")  # Replace with your actual password or app-specific password
            server.send_message(msg)
        logging.info(f"Email sent with {len(jobs)} job listings")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def job_scraping_task():
    companies = {
        "inmanage": "https://www.comeet.com/jobs/inmanage/B7.006",
        "buyme": "https://www.comeet.com/jobs/buyme/B2.008",
        "spark hire": "https://www.comeet.com/jobs/spark-hire/30.005",
        "okoora": "https://www.comeet.com/jobs/okoora/85.00C",
        "exodigo": "https://www.comeet.com/jobs/exodigo/89.005",
        # Add more companies using Comeet template here
    }

    all_new_jobs = []

    for company, url in companies.items():
        logging.info(f"Scraping jobs for {company}...")
        jobs = scrape_comeet_jobs(url, company)

        # Store new jobs in the database and get only the new jobs
        new_jobs = store_jobs_in_database(jobs)
        all_new_jobs.extend(new_jobs)

    if all_new_jobs:
        send_email_notification(all_new_jobs)
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
