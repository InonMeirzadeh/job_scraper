import json

# Load configuration from JSON file
with open("config/config.json", "r") as config_file:
    config_data = json.load(config_file)

DB_CONFIG = config_data["db_config"]
EMAIL_CONFIG = config_data["email_config"]
COMPANIES = config_data["companies"]
