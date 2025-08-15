import os
import django
import sys

# Add the parent directory of VmedulifeDashboard to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'dashboard_project')))

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
CONFIG_FILE = 'config.json'
SELECTORS_FILE = 'selectors.json'
ATTENDANCE_FILE = 'attendance.json'
DEBUG_HTML_FILE = 'debug.html'
LOGIN_URL = "https://portal.vmedulife.com/public/auth/#/login/Cvr-Telangana"

driver = None  # Initialize driver as None globally
wait = None    # Initialize wait as None globally

# Utility Functions
def read_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: {filepath} not found. Please create it.")
        exit()
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}. Please check file format.")
        exit()

def save_data(data, filepath):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Data successfully saved to {filepath}")
    except Exception as e:
        logging.error(f"Error saving data to {filepath}: {e}")

# Selenium Functions
def setup_driver():
    global driver, wait
    logging.info("Setting up WebDriver...")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        wait = WebDriverWait(driver, 10)  # Default wait of 10 seconds
        logging.info("WebDriver setup complete.")
    except Exception as e:
        logging.error(f"Error setting up WebDriver: {e}")
        exit()

def login():
    logging.info("Opening login page...")
    driver.get(LOGIN_URL)

    config = read_json_file(CONFIG_FILE)
    selectors = read_json_file(SELECTORS_FILE)

    try:
        logging.info("Entering credentials...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors["username_input"]))).send_keys(config["username"])
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors["password_input"]))).send_keys(config["password"])
        
        logging.info("Clicking login button...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors["login_button"]))).click()
        
        logging.info("Waiting for dashboard to load...")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors["dashboard_loaded_indicator"])))
        logging.info("Login successful!")
    except TimeoutException:
        logging.error("Login failed: Dashboard element not found. Saving HTML dump for debugging...")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.quit()
        exit()
    except Exception as e:
        logging.error(f"An error occurred during login: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.quit()
        exit()

def navigate_to_attendance_page():
    selectors = read_json_file(SELECTORS_FILE)
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
        driver.quit()
        exit()
    except Exception as e:
        logging.error(f"An error occurred during navigation: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.quit()
        exit()

def scrape_attendance():
    # selectors = read_json_file(SELECTORS_FILE) # Removed: selectors is now global
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

# Main execution
def main():
    global selectors # Declare selectors as global here as well
    
    config = read_json_file(CONFIG_FILE)
    selectors = read_json_file(SELECTORS_FILE)

    setup_driver()
    if driver is None or wait is None:
        logging.error("WebDriver was not set up correctly. Exiting.")
        exit()

    try:
        login()
        navigate_to_attendance_page()
        scrape_attendance() # The scrape_attendance function now saves directly to the DB

    except Exception as e:
        logging.error(f"An unexpected error occurred in main: {e}")
        with open(DEBUG_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    finally:
        logging.info("Scraping finished.")
        driver.quit()

if __name__ == "__main__":
    main()
