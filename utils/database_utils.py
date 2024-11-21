import psycopg2
from datetime import datetime
import logging
from config.config import DB_CONFIG


def connect_database():
    """
    Connects to the PostgreSQL database and returns the connection object.
    """
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        raise


def is_job_in_database(cursor, job):
    """
    Checks if the job already exists in the database.
    """
    query = """
        SELECT 1 FROM jobs WHERE company = %s AND title = %s AND location = %s AND link = %s
    """
    cursor.execute(query, (job['company'], job['title'], job['location'], job['link']))
    return cursor.fetchone() is not None


def store_new_jobs(jobs):
    """
    Stores new job listings in the database.
    """
    conn = connect_database()
    cursor = conn.cursor()
    new_jobs = []

    try:
        for job in jobs:
            if not is_job_in_database(cursor, job):
                cursor.execute("""
                    INSERT INTO jobs (company, title, location, link, date_posted)
                    VALUES (%s, %s, %s, %s, %s)
                """, (job['company'], job['title'], job['location'], job['link'], datetime.now()))
                new_jobs.append(job)

        conn.commit()
        logging.info(f"Stored {len(new_jobs)} new jobs in the database")
    finally:
        cursor.close()
        conn.close()

    return new_jobs
