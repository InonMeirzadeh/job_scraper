from selenium.webdriver.chrome.options import Options
from selenium import webdriver

def initialize_webdriver():
    """
    Initializes and returns a Chrome WebDriver instance with required options.
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration
    chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems

    return webdriver.Chrome(options=chrome_options)
