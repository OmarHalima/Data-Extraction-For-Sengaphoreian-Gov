import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

def safe_click_element(driver, wait, by, identifier):
    """
    Safely clicks an element by scrolling it into view and using JavaScript.
    Waits for any loading overlay to disappear. If the overlay persists,
    it removes the overlay.
    """
    try:
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.loadingoverlay")))
    except TimeoutException:
        print("Overlay did not disappear in time; attempting to remove it.")
        # Remove all overlay elements if still present
        driver.execute_script("""
            var overlays = document.querySelectorAll('div.loadingoverlay');
            overlays.forEach(function(overlay) { overlay.remove(); });
        """)
    
    element = wait.until(EC.element_to_be_clickable((by, identifier)))
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(1)  # Allow time for animations/overlays to settle
        driver.execute_script("arguments[0].click();", element)
    except ElementClickInterceptedException:
        time.sleep(1)
        driver.execute_script("arguments[0].click();", element)
    return element

def scrape_agency_details(start_page, end_page):
    # Define output directory and file paths
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
        
        # Instead of directly clicking the panel button,
        # use safe_click_element to handle the overlay.
        safe_click_element(driver, wait, By.ID, "eadHomeForm:j_id_16_a")
        
        current_page = 1
        
        # Navigate to the starting page if needed...
        while current_page < start_page:
            next_page_xpath = f"//span[contains(@class, 'pageNumber') and contains(text(), '{current_page + 1}')]"
            try:
                safe_click_element(driver, wait, By.XPATH, next_page_xpath)
                current_page += 1
                time.sleep(2)
            except Exception as e:
                print(f"Error navigating to starting page {start_page}: {e}")
                break
        
        # Process pages from start_page to end_page
        while current_page <= end_page:
            print(f"Processing page {current_page}")
            
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
            
            if current_page < end_page:
                next_page_xpath = f"//span[contains(@class, 'pageNumber') and contains(text(), '{current_page + 1}')]"
                try:
                    safe_click_element(driver, wait, By.XPATH, next_page_xpath)
                    current_page += 1
                    time.sleep(2)
                except TimeoutException:
                    print("No more pages found. Exiting pagination loop.")
                    break
                except Exception as e:
                    print(f"Error navigating to next page {current_page + 1}: {e}")
                    break
            else:
                break
                
    finally:
        driver.quit()

if __name__ == "__main__":
    # For example, this file scrapes pages 201 to 300.
    scrape_agency_details(start_page=401, end_page=500)
