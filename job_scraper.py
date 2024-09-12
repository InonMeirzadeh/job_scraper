from datetime import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2
import schedule
import time
import smtplib
from email.mime.text import MIMEText
import spacy
import logging

# Load the SpaCy model for English
nlp = spacy.load('en_core_web_sm')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_valid_job_title(title):
    """
    Uses NLP to determine if a title is a valid job title and contains 'junior'.
    Falls back to simple keyword matching if necessary.
    """
    doc = nlp(title)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            return False
    return 'junior' in title.lower()


def is_valid_location(location):
    """
    Uses NLP to determine if a location mentions 'Israel'.
    Falls back to simple keyword matching if necessary.
    """
    doc = nlp(location)
    for ent in doc.ents:
        if ent.label_ == "GPE" and 'israel' in ent.text.lower():
            return True
    return 'israel' in location.lower()


def extract_text(element):
    """
    Extracts and cleans text from an HTML element.
    Handles cases where the element is None.
    """
    return element.text.strip() if element else ''


def scrape_job_postings(url, company_name):
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

    # Targeting potential containers for job postings
    potential_containers = ['div', 'section', 'article']
    possible_classes = ['job', 'career', 'position', 'listing', 'opening', 'vacancy', 'recruitment']

    jobs = []

    for container in potential_containers:
        for class_name in possible_classes:
            job_elements = soup.find_all(container, class_=lambda c: c and class_name in c.lower())

            for job_element in job_elements:
                title_element = job_element.find(['h1', 'h2', 'h3', 'a', 'span'], string=True)
                location_element = job_element.find(['span', 'div', 'p'], string=lambda s: s and any(
                    loc in s.lower() for loc in ['location', 'city', 'place', 'state', 'country', 'region']))
                description_element = job_element.find(['p', 'div'], string=True)
                link_tag = job_element.find('a', href=True)

                title = extract_text(title_element)
                location = extract_text(location_element)
                description = extract_text(description_element)

                if is_valid_job_title(title) and is_valid_location(location):
                    job = {
                        'company': company_name,
                        'title': title,
                        'location': location,
                        'description': description,
                        'link': link_tag['href'] if link_tag else url
                    }
                    jobs.append(job)

    # Fallback Mechanism: Checking for data in script tags (potentially embedded JSON)
    if not jobs:
        logging.info(f"No jobs found using initial method for {company_name}. Trying to extract from script tags.")
        scripts = soup.find_all('script')
        for script in scripts:
            if 'application/ld+json' in script.get('type', ''):
                json_data = script.string.strip()
                # Implement parsing logic here if needed, depending on the JSON structure
                # You could use json.loads() to parse and check for job postings

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


def send_email_notification(jobs):
    """
    Sends an email notification with the new job postings.
    """
    sender = "inon164@gmail.com"
    receiver = "inon164@gmail.com"
    subject = "New Job Postings"
    body = "Here are the new job postings:\n\n"
    for job in jobs:
        body += f"Company: {job['company']}\nTitle: {job['title']}\nLocation: {job['location']}\nDescription:" \
                f" {job['description']}\nLink: {job['link']}\n\n"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, "*****")
        server.send_message(msg)


def job_scraping_task():
    companies = {
        "moonactive": "https://www.moonactive.com/careers/?dept=r-d&loc=tel-aviv,-israel",
        "cisco": "https://jobs.cisco.com/jobs/SearchJobs/",
        "roojoom": "https://www.roojoom.com/careers/"
    }

    all_jobs = []
    for company, url in companies.items():
        logging.info(f"Scraping jobs for {company}...")
        jobs = scrape_job_postings(url, company)
        all_jobs.extend(jobs)

    if all_jobs:
        store_jobs_in_database(all_jobs)
        send_email_notification(all_jobs)


def main():
    job_scraping_task()
    schedule.every(1).minutes.do(job_scraping_task)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
