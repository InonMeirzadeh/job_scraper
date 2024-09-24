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


def is_valid_job(title, location, experience_level):
    """
    Checks if the job is a junior position in Israel.
    """
    # Define keywords to capture junior-level positions
    junior_keywords = ['junior', 'entry-level', 'associate', 'graduate', 'מתחיל', 'זוטר']
    # Define keywords for locations in Israel
    location_keywords = ['israel', 'tel aviv', 'jerusalem', 'haifa', 'bnei brak', 'champion tower',
                         'ramat gan','Hod HaSharon', 'TLV','rehovot', 'Herzliya', 'Or Yehuda']

    # Convert title and location to lowercase for case-insensitive matching
    title_lower = title.lower()
    location_lower = location.lower()

    # Check if any of the junior keywords and location keywords are present
    is_junior = any(keyword in title_lower for keyword in junior_keywords) or experience_level == 'Entry-level'

    if experience_level == 'Not specified' and 'junior' in title_lower:
        is_junior = True
        logging.info(f"Job with 'Junior' in title processed despite missing experience level: {title}")

    is_in_israel = any(keyword in location_lower for keyword in location_keywords)

    # Add debug logs to see why a job might be skipped
    if not is_junior:
        logging.warning(f"Skipping job due to non-junior criteria: {title}")
    if not is_in_israel:
        logging.warning(f"Skipping job due to non-Israel location: {location}")

    return is_junior and is_in_israel


def scrape_comeet_jobs(url, company_name):
    # Set up Chrome options
    chrome_options = Options()
    # Uncomment to see the browser in action
    # chrome_options.add_argument('--headless')  # Run in headless mode (no GUI)
    chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration
    chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems

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

        # Find all job listings using the 'positionItem' class
        job_listings = soup.find_all('a', class_='positionItem')

        logging.info(f"Found {len(job_listings)} potential job listings in the page for {company_name}")

        for job in job_listings:
            # Extract job title
            title_text = job.find('span', class_='positionLink').get_text(strip=True) if job.find('span',
                                                                                                  class_='positionLink') else ''

            # Extract job link
            job_link = job['href'] if job.has_attr('href') else ''

            # Find the parent container to locate location and experience details
            parent = job.find_parent()

            # Extract job location by finding the 'fa fa-map-marker' icon's parent
            location_element = parent.find('i', class_='fa fa-map-marker')
            location_text = location_element.find_next_sibling(string=True).strip() if location_element else ''

            # Extract experience level using more precise text search
            experience_element = parent.find(string=re.compile(r'\b(Entry-level|Mid-level|Senior)\b'))
            experience_level = experience_element.strip() if experience_element else 'Not specified'

            # Extract employment type
            employment_type_element = parent.find(string=re.compile(r'\b(Full-time|Part-time|Contract)\b'))
            employment_type = employment_type_element.strip() if employment_type_element else ''

            if experience_level == 'Not specified':
                logging.warning(f"Experience level not found for job: {title_text}")
            logging.info(f"Processing job: {title_text} in {location_text} with experience level {experience_level}")

            if is_valid_job(title_text, location_text, experience_level):
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
            else:
                logging.info(f"Skipping non-junior job: {title_text}")

        if jobs:
            logging.info(f"Found {len(jobs)} valid junior jobs for {company_name}")
        else:
            logging.error(f"No valid job data found for {company_name}")

        return jobs

    finally:
        driver.quit()


def is_job_in_database(cursor, job):
    """
    Checks if the job is already in the database.
    """
    cursor.execute("""
        SELECT * FROM jobs
        WHERE company = %s AND title = %s AND location = %s AND link = %s
    """, (job['company'], job['title'], job['location'], job['link']))
    return cursor.fetchone() is not None


def store_new_jobs_in_database(jobs):
    """
    Stores only new job postings in the PostgreSQL database.
    Returns a list of newly added jobs.
    """
    conn = psycopg2.connect(
        dbname='job_scraper',
        user='postgres',
        password='***',
        host='localhost',
        port='5432'
    )
    cursor = conn.cursor()
    new_jobs = []

    for job in jobs:
        if not is_job_in_database(cursor, job):
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
    return new_jobs


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
            server.login(sender, "***")
            server.send_message(msg)
        logging.info(f"Email sent with {len(jobs)} new job listings")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def job_scraping_task():
    companies = {
        "inmanage": "https://www.comeet.com/jobs/inmanage/B7.006",
        "buyme": "https://www.comeet.com/jobs/buyme/B2.008",
        "spark hire": "https://www.comeet.com/jobs/spark-hire/30.005",
        "okoora": "https://www.comeet.com/jobs/okoora/85.00C",
        "exodigo": "https://www.comeet.com/jobs/exodigo/89.005",
        "dreamedai": "https://www.comeet.com/jobs/dreamedai/B9.002",
        "chaoslabs": "https://www.comeet.com/jobs/chaoslabs/E8.007",
        "novidea": "https://www.comeet.com/jobs/novidea/E5.00A",
        "biocatch": "https://www.comeet.com/jobs/biocatch/03.00E",
        "nova": "https://www.comeet.com/jobs/nova/A5.007",
        "cellebrite": "https://www.comeet.com/jobs/Cellebrite/C3.00F",
        "hunters": "https://www.comeet.com/jobs/hunters/67.007",
        "moonactive": "https://www.comeet.com/jobs/moonactive/A2.00C",
        "superplay": "https://www.comeet.com/jobs/superplay/28.003",
        "matific": "https://www.comeet.com/jobs/matific/62.000",
        "monday": "https://www.comeet.com/jobs/monday/41.00B",
        "888jobs": "https://www.comeet.com/jobs/888jobs/E2.001",
        "global-e": "https://www.comeet.com/jobs/global-e/62.002",
        "cellebrite": "https://www.comeet.com/jobs/Cellebrite/C3.00F",
        "minutemedia": "https://www.comeet.com/jobs/minutemedia/45.00A",
        "kaltura": "https://www.comeet.com/jobs/kaltura/E2.00D",
        "silk": "https://www.comeet.com/jobs/silk/F6.00C",
        "tikalk": "https://www.comeet.com/jobs/tikalk/68.00C",
        "spark-hire": "https://www.comeet.com/jobs/spark-hire/30.005",
        "chargeflow": "https://www.comeet.com/jobs/chargeflow/29.001",
        "team8": "https://www.comeet.com/jobs/team8/61.003",
        "tictuk": "https://www.comeet.com/jobs/tictuk/78.002",
        "atera": "https://www.comeet.com/jobs/atera/63.00B",
        "etoro": "https://www.comeet.com/jobs/etoro/41.009",
        "lusha": "https://www.comeet.com/jobs/lusha/73.00B",
        "365scores": "https://www.comeet.com/jobs/365scores/B3.006",
        "wsc-sports": "https://www.comeet.com/jobs/wsc-sports/93.007",
        "audiocodes": "https://www.comeet.com/jobs/audiocodes/85.004",
        "scaleops": "https://www.comeet.com/jobs/scaleops/99.003",
        "finout": "https://www.comeet.com/jobs/finout/07.006",
        "ox_security": "https://www.comeet.com/jobs/ox_security/F8.006",
        # Add more companies using Comeet template here
    }

    all_jobs = []
    for company, url in companies.items():
        logging.info(f"Scraping jobs for {company}...")
        jobs = scrape_comeet_jobs(url, company)
        all_jobs.extend(jobs)

    if all_jobs:
        new_jobs = store_new_jobs_in_database(all_jobs)
        if new_jobs:
            send_email_notification(new_jobs)
        else:
            logging.info("No new jobs to add to the database or send email about")
    else:
        logging.info("No junior jobs found in Israel")


def main():
    job_scraping_task()
    schedule.every(50).minutes.do(job_scraping_task)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
