# Job Scraper

This project is a Python-based web scraper designed to extract junior-level job listings from various companies using the Comeet platform. The scraper fetches job listings, filters for junior positions located in Israel, stores the new jobs in a PostgreSQL database, and sends email notifications about newly found positions.

## Features

- Scrapes junior-level jobs from multiple companies' career pages on Comeet.
- Filters jobs based on location in Israel and junior-level experience.
- Stores only new job postings in a PostgreSQL database.
- Sends an email notification with the new job postings found.
- Can be scheduled to run at regular intervals using `schedule`.

## Requirements

- Python 3.x
- PostgreSQL
- Google Chrome browser and ChromeDriver

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/job_scraper.git
    cd job_scraper
    ```

2. Set up a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Download the appropriate version of [ChromeDriver](https://chromedriver.chromium.org/downloads) for your Chrome browser version and make sure it's in your system's PATH.

5. Set up the PostgreSQL database:
    - Create a new database named `job_scraper`.
    - Configure the database connection in the script (`store_new_jobs_in_database()`).

## Configuration

Update the following information in the script before running:

- **Database connection**: Update the `dbname`, `user`, `password`, `host`, and `port` in the `store_new_jobs_in_database()` function to match your PostgreSQL setup.
- **Email Settings**: Update the sender's email, receiver's email, and password for the email notification system in `send_email_notification()`. Use your email service's SMTP settings (currently set for Gmail).

## Usage

To run the job scraper:

```bash
python job_scraper.py

The script will:

Scrape job listings from each company listed in the companies dictionary.
Filter for junior jobs located in Israel.
Store newly found jobs in a PostgreSQL database.
Send an email with details of the new job listings.
The scraper is scheduled to run at regular intervals using the schedule library. You can modify the interval in the main() function, which is currently set to run every minute.

Logging
All scraping activity is logged, including:

When a page is being scraped.
Jobs that are found, processed, and stored.
Warnings when experience levels or locations cannot be found.
Errors during the scraping or email sending process.

Adding More Companies
To add more companies to the scraping process, simply add their Comeet job listing URL and company name to the companies dictionary in the job_scraping_task() function. The URLs should follow the Comeet format.

companies = {
    "newcompany": "https://www.comeet.com/jobs/newcompany/XX.XXX",
    ...
}
Contributing
Contributions are welcome! If you find any issues or want to add more features, feel free to open a pull request or issue.
