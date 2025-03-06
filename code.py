import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

def safe_click_element(driver, wait, by, identifier):
    """
    Scrolls the element into view, waits for any loading overlay to vanish,
    and clicks the element using JavaScript.
    """
    try:
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.loadingoverlay")))
    except TimeoutException:
        print("Overlay did not disappear in time; attempting to remove it.")
        driver.execute_script("""
            var overlays = document.querySelectorAll('div.loadingoverlay');
            overlays.forEach(function(overlay) { overlay.remove(); });
        """)
    element = wait.until(EC.element_to_be_clickable((by, identifier)))
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", element)
    except ElementClickInterceptedException:
        time.sleep(1)
        driver.execute_script("arguments[0].click();", element)
    return element

def navigate_to_page_by_next(driver, wait, target_page):
    """
    Attempts to navigate to the target page number by repeatedly clicking the next arrow.
    It looks for a page number element using an XPath that normalizes its text (to remove &nbsp;).
    Once the target page element is present, it is clicked.
    """
    print(f"Attempting to navigate to page {target_page} by clicking next repeatedly.")
    # The target element: e.g., <span class="pageNumber dxd-mom-phone inactive">&nbsp;501</span>
    xpath_target = f"//span[contains(@class, 'pageNumber') and normalize-space(text())='{target_page}']"
    max_attempts = 1000  # adjust if needed
    attempts = 0

    while attempts < max_attempts:
        try:
            elems = driver.find_elements(By.XPATH, xpath_target)
            if elems:
                print(f"Found target page element for page {target_page}. Clicking it.")
                # Even if the element is non-clickable by default, try clicking via JavaScript.
                driver.execute_script("arguments[0].click();", elems[0])
                time.sleep(2)
                return True
            else:
                print(f"Target page {target_page} not found. Clicking next arrow (attempt {attempts+1}).")
                next_arrow = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.ui-paginator-next")))
                driver.execute_script("arguments[0].scrollIntoView(true);", next_arrow)
                time.sleep(1)
                next_arrow.click()
                time.sleep(2)
                attempts += 1
        except Exception as e:
            print(f"Error while navigating: {e}")
            attempts += 1

    print("Failed to navigate to target page after many attempts.")
    return False

def scrape_agency_details(start_page, end_page):
    # Define output directory and file paths.
    output_dir = os.path.join(os.getcwd(), f"Scraper_{start_page}_{end_page}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    ids_file_path = os.path.join(output_dir, f"agency_ids_{start_page}_{end_page}.txt")
    details_file_path = os.path.join(output_dir, f"agency_details_{start_page}_{end_page}.txt")
    
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 10)
    visited = set()
    agency_details = {}
    
    try:
        driver.get("https://service2.mom.gov.sg/eadirectory/")
        # Click the panel button.
        safe_click_element(driver, wait, By.ID, "eadHomeForm:j_id_16_a")
        time.sleep(2)
        
        # Assume we start at page 1.
        current_page = 1
        print(f"Currently at page {current_page}")
        
        # If start_page > current_page, use the next-arrow loop to navigate.
        if start_page > current_page:
            if not navigate_to_page_by_next(driver, wait, start_page):
                print("Could not navigate to the desired start page.")
                return
            current_page = start_page
        
        # Main scraping loop.
        while current_page <= end_page:
            print(f"Scraping page {current_page}")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-commandlink.ui-widget.cardAgencyName")))
            agency_elements = driver.find_elements(By.CSS_SELECTOR, ".ui-commandlink.ui-widget.cardAgencyName")
            
            page_agency_ids = []
            for elem in agency_elements:
                agency_id = elem.get_attribute("id")
                if agency_id and agency_id not in visited:
                    page_agency_ids.append(agency_id)
                    visited.add(agency_id)
            
            if page_agency_ids:
                with open(ids_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Page {current_page}: " + ",".join(page_agency_ids) + "\n")
            
            for agency_id in page_agency_ids:
                try:
                    safe_click_element(driver, wait, By.ID, agency_id)
                except Exception as e:
                    print(f"Error clicking agency id {agency_id}: {e}")
                    continue
                
                try:
                    detail_div = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".dxd-mom-columns.dxd-mom-three.dxd-mom-agency-location.dxd-mom-hard.contactBorderLeft.contactBorderTop")
                    ))
                    details_text = detail_div.text
                except TimeoutException as e:
                    print(f"Timeout scraping details for agency id {agency_id}: {e}")
                    details_text = "N/A"
                except Exception as e:
                    print(f"Error scraping details for agency id {agency_id}: {e}")
                    details_text = "N/A"
                
                try:
                    name_element = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.dxd-mom-columns.dxd-mom-eleven h2.eaName")
                    ))
                    agency_name = name_element.text.strip()
                except Exception as e:
                    print(f"Error extracting agency name for agency id {agency_id}: {e}")
                    agency_name = "N/A"
                
                agency_details[agency_id] = {"name": agency_name, "details": details_text}
                with open(details_file_path, "a", encoding="utf-8") as f:
                    f.write(f"Page {current_page} - Agency ID: {agency_id}\n")
                    f.write(f"Agency Name: {agency_name}\n")
                    f.write(f"Agency Details: {details_text}\n\n")
                
                try:
                    safe_click_element(driver, wait, By.CSS_SELECTOR, ".ui-commandlink.ui-widget.backLink.dxd-mom-back-page-nav")
                except Exception as e:
                    print(f"Error navigating back from agency id {agency_id}: {e}")
                    driver.back()
                
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-commandlink.ui-widget.cardAgencyName")))
                time.sleep(1)
            
            # Navigate to the next page if we haven't reached end_page.
            if current_page < end_page:
                next_page = current_page + 1
                if not navigate_to_page_by_next(driver, wait, next_page):
                    print("Could not navigate to the next page.")
                    break
                current_page = next_page
            else:
                break
                
    finally:
        driver.quit()

if __name__ == "__main__":
    # This configuration will attempt to scrape pages 501 to 550.
    scrape_agency_details(start_page=501, end_page=550)
