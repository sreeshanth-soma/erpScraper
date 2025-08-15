import os
import django
import sys

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(__file__)

# Add the parent directory of VmedulifeDashboard to the Python path
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, 'dashboard_project')))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VmedulifeDashboard.settings')
django.setup()

from attendance_dashboard.models import AttendanceData

import json
import logging
import re # Import the re module
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global Constants
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
SELECTORS_FILE = os.path.join(SCRIPT_DIR, 'selectors.json')
ATTENDANCE_FILE = os.path.join(SCRIPT_DIR, 'attendance.json')
DEBUG_HTML_FILE = os.path.join(SCRIPT_DIR, 'debug.html')
LOGIN_URL = "https://portal.vmedulife.com/public/auth/#/login/Cvr-Telangana"

# Utility Functions (moved here to be defined before global use)
def read_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: {filepath} not found. Please create it.")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}. Please check file format.")
        return None

driver = None  # Initialize driver as None globally
wait = None    # Initialize wait as None globally
selectors = read_json_file(SELECTORS_FILE) # Load selectors globally
config = read_json_file(CONFIG_FILE) # Load config globally

def save_data(data, filepath):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Data successfully saved to {filepath}")
    except Exception as e:
        logging.error(f"Error saving data to {filepath}: {e}")

def dump_html_for_debug(html_content):
    try:
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        logging.info(f"Current page HTML dumped to {DEBUG_HTML_FILE} for debugging.")
    except Exception as e:
        logging.error(f"Error dumping HTML for debug: {e}")

# Selenium Functions
def setup_driver():
    global driver, wait
    logging.info("Setting up WebDriver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        wait = WebDriverWait(driver, 10)  # Default wait of 10 seconds
        logging.info("WebDriver setup complete.")
        return driver, wait # Return driver and wait
    except Exception as e:
        logging.error(f"Error setting up WebDriver: {e}")
        return None, None # Return None on error

def login(username, password):
    global selectors # Declare selectors as global
    global dump_html_for_debug # Declare dump_html_for_debug as global

    if selectors is None:
        raise Exception("Selectors could not be loaded. Check selectors.json.")

    logging.info("Navigating to login page...")
    driver.get(LOGIN_URL)
    
    try:
        logging.info("Filling in username and password...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['username_input']))).send_keys(username)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['password_input']))).send_keys(password)
        
        logging.info("Clicking login button...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors['login_button']))).click()
        
        logging.info("Waiting for dashboard to load...")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors['dashboard_loaded_indicator'])))
        logging.info("Successfully logged in and dashboard loaded.")
    except TimeoutException:
        logging.error("Timeout during login. Dashboard indicator not found.")
        dump_html_for_debug(driver.page_source)
        raise # Re-raise the exception to be caught in main or calling function
    except Exception as e:
        logging.error(f"An error occurred during login: {e}")
        dump_html_for_debug(driver.page_source)
        raise # Re-raise the exception

def navigate_to_attendance_page():
    global selectors # Declare selectors as global
    global dump_html_for_debug # Declare dump_html_for_debug as global
    # selectors = read_json_file(SELECTORS_FILE) # Removed: selectors is now global
    if selectors is None: # Handle case where selectors file read fails
        raise Exception("Selectors could not be loaded.")

    try:
        logging.info("Clicking on modules dropdown icon...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors["modules_dropdown_icon"]))).click()
        
        logging.info("Navigating to attendance page via Academic Planning link...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors["attendance_link"]))).click()
        logging.info("Clicked on Academic Planning link.")

        # New step: Click 'View Subjects' button for the first group
        logging.info("Clicking 'View Subjects' button for the first group...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".group-card button.btn"))).click()
        logging.info("Clicked 'View Subjects' button.")
        
        # Wait for the subject list modal/sidebar to appear (assuming it has an ID 'group-subjects-modal')
        wait.until(EC.visibility_of_element_located((By.ID, 'group-subjects-modal')))
        logging.info("Subject list modal/sidebar appeared.")

        # Wait for the content within the subject list modal to load
        wait.until(EC.visibility_of_element_located((By.ID, 'group-subject-list')))
        logging.info("Subject list content loaded.")

    except TimeoutException:
        logging.error("Navigation to attendance page failed: Element not found. Saving HTML dump for debugging...")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise # Re-raise the exception
    except Exception as e:
        logging.error(f"An error occurred during navigation: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise # Re-raise the exception

def scrape_attendance():
    global selectors # Declare selectors as global
    global dump_html_for_debug # Declare dump_html_for_debug as global

    if selectors is None:
        raise Exception("Selectors could not be loaded. Check selectors.json.")

    logging.info("Extracting attendance data...")
    total_classes_conducted = 0
    classes_attended = 0
    attendance_percentage = "N/A"

    # Wait for the total group attendance summary to be visible and contain text
    logging.info("Waiting for overall attendance summary to load...")
    wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, selectors['total_group_attendance_summary']), "%"))
    logging.info("Overall attendance summary loaded.")

    try:
        # Extract data from individual subject attendance elements
        subject_attendance_elements = WebDriverWait(driver, 20).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, selectors['subject_attendance_info']))
        )

        for element in subject_attendance_elements:
            # Wait for the preloader image to disappear from within this specific subject element
            preloader_selector = f"#{element.get_attribute('id')} img[src*='Ring-Preloader']"
            logging.debug(f"Waiting for preloader to disappear in {element.get_attribute('id')} using selector: {preloader_selector}")
            try:
                WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, preloader_selector)))
                logging.debug(f"Preloader disappeared for {element.get_attribute('id')}")
            except TimeoutException:
                logging.warning(f"Timeout waiting for preloader to disappear for {element.get_attribute('id')}. Proceeding anyway.")

            # Now that preloader is likely gone, wait for the actual text pattern to appear
            wait.until(EC.text_to_be_present_in_element((By.ID, element.get_attribute('id')), "Present session "))

            text = element.get_attribute('outerHTML') # Get outerHTML to capture the element itself and its content
            logging.debug(f"Processing element outerHTML: {text}") # Debugging line
            # Example outerHTML: "<div id="viewSession_..." >Present session <b>10</b> out of <b>15</b> | Percentage <b>66.67%</b></b></div>"
            match = re.search(r"Present session <b>(\d+) out of (\d+) \| Percentage <b>([\d.]+)%</b></b>", text)
            if match:
                try:
                    attended_str = match.group(1)
                    total_str = match.group(2)
                    percentage_str = match.group(3)
                    
                    classes_attended += int(attended_str)
                    total_classes_conducted += int(total_str)
                    logging.debug(f"Parsed: Attended={attended_str}, Total={total_str}, Percentage={percentage_str} from {text}")
                except ValueError as ve:
                    logging.warning(f"Could not parse attendance numbers from: {text}. Error: {ve}")
            else:
                logging.warning(f"Attendance pattern not found in: {text}")

        if total_classes_conducted > 0:
            attendance_percentage = round((classes_attended / total_classes_conducted * 100), 2)
        
        # Create and save an AttendanceData object instead of returning a dictionary
        attendance_record = AttendanceData.objects.create(
            total_classes_conducted=total_classes_conducted,
            classes_attended=classes_attended,
            attendance_percentage=attendance_percentage
        )
        logging.info(f"Attendance data saved to Django database: {attendance_record}")
        return attendance_record # Return the Django model instance

    except Exception as e:
        logging.error(f"Failed to extract attendance data: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return None

def teardown_driver():
    global driver
    if driver:
        logging.info("Quitting WebDriver...")
        driver.quit()
        driver = None

# Main execution
def main():
    global selectors # Declare selectors as global here as well
    global config # Declare config as global here as well
    
    # config and selectors are already loaded globally at the top of the file
    # config = read_json_file(CONFIG_FILE)
    # if config is None:
    #     logging.error("Config file could not be loaded. Exiting.")
    #     return
    
    # selectors is already loaded globally at the top of the file
    # selectors = read_json_file(SELECTORS_FILE)

    if config is None:
        logging.error("Config file could not be loaded globally. Exiting.")
        return
    if selectors is None:
        logging.error("Selectors file could not be loaded globally. Exiting.")
        return

    setup_driver()
    if driver is None or wait is None:
        logging.error("WebDriver was not set up correctly. Exiting.")
        return # Exit main function gracefully

    try:
        login(config["username"], config["password"])
        navigate_to_attendance_page()
        scrape_attendance() # The scrape_attendance function now saves directly to the DB

    except Exception as e:
        logging.error(f"An unexpected error occurred in main: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    finally:
        logging.info("Scraping finished.")
        teardown_driver()

if __name__ == "__main__":
    main()
