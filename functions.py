import configparser
import importlib
import json
import os
import time
import uuid

from redis import Redis
from rq import Queue
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from models import CrawledData, JobInstance

redis_conn = Redis()
crawl_queue = Queue('crawl_queue', connection=redis_conn)
scrape_queue = Queue('scrape_queue', connection=redis_conn)

# Local SQLite database connection
engine = create_engine('sqlite:///crawlx.db')
Session = sessionmaker(bind=engine)
session = Session()

async def crawl_urls(url, crawler_name, job_instance_id):
    # Load the appropriate crawler module dynamically based on the crawler_name
    module_name = f"crawlers.{crawler_name}"
    try:
        crawler_module = importlib.import_module(module_name)
        # Execute the crawl logic specific to the custom crawler
        async for crawled_url in crawler_module.crawl(url):
            print("tasks :" + crawled_url)
            # Your code that interacts with the database
            new_instance = CrawledData(instance_id=job_instance_id, url=crawled_url)
            session.add(new_instance)
            session.commit()

            # Enqueue the scrape task immediately for each URL as it's found
            scrape_queue.enqueue(scrape_page, crawled_url, job_instance_id)
    except ImportError as e:
        print(e)
        print(f"Custom crawler '{crawler_name}' not found")        


def scrape_page(url, job_instance_id):
    driver = webdriver.Firefox()
    try:
        scrape_website(url, driver, job_instance_id)
    finally:
        driver.quit()
    print(f"Scraped data from {url}")


def extract_simplified_text(driver):
    text_fragments = []
    paragraphs = driver.find_elements(By.CSS_SELECTOR, 'p')
    for paragraph in paragraphs:
        text_fragments.append(paragraph.text)
    simplified_text = ' '.join(text_fragments)
    simplified_text = ' '.join(simplified_text.split())
    return simplified_text


def scrape_website(url, driver, job_instance_id):
    max_retry_count = 3
    retry_delay = 10
    data_dir = f"./{job_instance_id}"
    os.makedirs(data_dir, exist_ok=True)

    for retry in range(max_retry_count):
        try:
            driver.get(url)
            time.sleep(15)
            driver.implicitly_wait(10)

            prev_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == prev_height:
                    break
                prev_height = new_height

            time.sleep(5)

            simplified_text = extract_simplified_text(driver)
            website_title = driver.title

            data_id = uuid.uuid4()
            result_filename = os.path.join(data_dir, f"{data_id}_content.json")
            html_filename = os.path.join(data_dir, f"{data_id}_original.html")

            data = {
                'title': website_title,
                'url': url,
                'body': simplified_text
            }

            with open(result_filename, 'w') as f:
                json.dump(data, f)
            with open(html_filename, 'w') as f:
                f.write(driver.page_source)

            print(f"Website '{url}' scraped successfully!")
            data_to_update = session.query(CrawledData).filter_by(instance_id=job_instance_id, url=url).first()
            all_tasks_completed = all(job.args[1] != job_instance_id for job in scrape_queue.jobs)

            if all_tasks_completed:
                time.sleep(20)
                job_instance_data = session.query(JobInstance).filter_by(instance_id=job_instance_id).first()
                job_instance_data.status = "COMPLETED"
                job_instance_data.end_time = func.now()
                session.commit()
            else:
                print(f"Remaining jobs:  {str(len(scrape_queue.jobs))}")

            if data_to_update:
                data_to_update.raw_os_path = result_filename
                data_to_update.scraped_os_path = html_filename
                session.commit()
            else:
                new_data = CrawledData(
                    instance_id=job_instance_id,
                    url=url,
                    raw_os_path=result_filename,
                    scraped_os_path=html_filename)
                session.add(new_data)
                session.commit()
                print("New Data Added.")
            break

        except WebDriverException as e:
            print(f"Error occurred while scraping URL: {url}")
            print(f"Error message: {str(e)}")
            if retry < max_retry_count - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
        except Exception as e:
            print(f"Error occurred while scraping URL: {url}")
            print(f"Error message: {str(e)}")