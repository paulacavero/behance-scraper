from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime
import csv
import re

# Start Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Load the Behance job list
url = 'https://www.behance.net/joblist?tracking_source=nav20'  # Link to the Behance job list
driver.get(url)

# Configuration of the number of jobs to review and recent days to filter
recent_days = 30
desired_number = 600  # Total jobs to review on the website
reviewed_links = []  # All reviewed links, regardless of the days filter
found_links = []  # Links that meet the day filter
saved_jobs = []
cycles_without_new_links = 0  # Counter to detect when no new jobs are loading

# Keyword to search in the job description
keyword = "" # Add the keyword you want to search in the job description  


try:
    # Wait up to 20 seconds for the first job link to appear
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "JobCard-jobCardLink-Ywm"))
    )

    # Scrolling loop to capture up to the desired number of jobs
    while len(reviewed_links) < desired_number and cycles_without_new_links < 5:
        # Execute scroll down and wait to load new content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(5)  # Increase the time to ensure new elements load

        # Get the HTML of the current page
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Save the number of links reviewed before this page
        previous_links = len(reviewed_links)

        # Process each job and extract the link
        for job_card in soup.find_all('a', class_='JobCard-jobCardLink-Ywm'):
            link = job_card['href']
            full_url = f"https://www.behance.net{link}"
            
            # Check if we have already reviewed this link
            if full_url not in reviewed_links:
                reviewed_links.append(full_url)  # Add to the reviewed list

                # Now check if it meets the `recent_days` filter
                aria_label = job_card.get('aria-label', '')
                days_published = None

                '''Make sure the website is in English to match the text patterns, if not, you should chamge the patterns'''

                if "ago" in aria_label:
                    if re.search(r'(\d+)\s*days?', aria_label):  # Matches "X days ago"
                        days_published = int(re.search(r'(\d+)\s*days?', aria_label).group(1))
                    elif re.search(r'one\s*month', aria_label):  # Matches "one month ago"
                        days_published = 30
                    elif re.search(r'(\d+)\s*months?', aria_label):  # Matches "X months ago"
                        days_published = int(re.search(r'(\d+)\s*months?', aria_label).group(1)) * 30
                    elif re.search(r'(\d+)\s*hours?', aria_label):  # Matches "X hours ago"
                        days_published = 0  # Published today if the time is in hours

                # If the previous method didn't work, try to find the time in the job page
                if days_published is None:
                    time_element = job_card.find_next('span', class_='JobCard-time-Cvz')
                    if time_element:
                        time_text = time_element.text.strip()
                        if re.search(r'(\d+)\s*days?', time_text):
                            days_published = int(re.search(r'(\d+)\s*days?', time_text).group(1))
                        elif re.search(r'one\s*month', time_text):
                            days_published = 30
                        elif re.search(r'(\d+)\s*months?', time_text):
                            days_published = int(re.search(r'(\d+)\s*months?', time_text).group(1)) * 30
                        elif re.search(r'(\d+)\s*hours?', time_text):
                            days_published = 0

                # Add to `found_links` only if it meets the days filter
                if days_published is not None and days_published <= recent_days:
                    found_links.append(full_url)

        # Check if new links were found in this cycle
        if len(reviewed_links) == previous_links:
            cycles_without_new_links += 1  # Increment if no new links were found
        else:
            cycles_without_new_links = 0  # Reset if new links were found

    # Display the total number of reviewed links and recent links found
    print(f"Total reviewed links: {len(reviewed_links)}")
    print(f"Total recent links found (less than {recent_days} days): {len(found_links)}")

    # Access each recent link and check for the keyword 
   
    for full_url in found_links:
        driver.get(full_url)
        sleep(2)  # Wait for the job page to load

        # Extract the HTML of the job page and analyze the content
        job_html = driver.page_source
        job_soup = BeautifulSoup(job_html, 'html.parser')

        # Check for the keyword in the job description
        if keyword in job_soup.text:
            print(f"Job meets the condition: {full_url}")

            # Extract the link and the company name
            saved_company_link = None
            company_name = None
            company_link = job_soup.find('a', class_='JobDetailContent-companyNameLink-EUx')
            if company_link:
                saved_company_link = company_link["href"]
                company_name = company_link.text.strip()
                # Remove the extra text "opens in a new tab" if present
                company_name = company_name.replace("opens in a new tab", "").strip()

            # Save the data to the job list
            saved_jobs.append({
                'job_link': full_url,
                'company_link': saved_company_link,
                'company_name': company_name
            })

    print(f'Saved job list: {saved_jobs}')

finally:
    # Close the browser at the end
    driver.quit()

# Save to CSV
csv_filename = 'behance_jobs.csv'  # Add your local path to save the CSV file
existing_links = set()

# Ensure the CSV file exists
try:
    with open(csv_filename, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            existing_links.add(row['job_link'])
except FileNotFoundError:
    print('File not found. Creating a new file.')
    # Create the file with headers if it doesn't exist
    with open(csv_filename, mode='w', newline='', encoding='utf-8-sig') as file:
        fieldnames = ['job_link', 'company_name', 'company_link', 'stored_date']
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=',')
        writer.writeheader()  # Write header to the new file

# Append new data to the file
with open(csv_filename, mode='a', newline='', encoding='utf-8-sig') as file:
    fieldnames = ['job_link', 'company_name', 'company_link', 'stored_date']
    writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=',')
    if file.tell() == 0:
        writer.writeheader()  # Write header if file was empty

    for job in saved_jobs:
        if job['job_link'] not in existing_links:
            job['stored_date'] = datetime.now().strftime('%Y-%m-%d')
            writer.writerow(job)