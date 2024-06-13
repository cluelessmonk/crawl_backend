import asyncio
import time
import os

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# Initialize the URL set
url_set = set()


async def scrape_urls(driver):
    anchors = driver.find_elements(By.TAG_NAME, 'a')
    new_urls = set()
    for anchor in anchors:
        href = anchor.get_attribute('href')
        if href and href.startswith('https://careers.oracle.com/jobs/#en/sites/jobsearch/job'):
            if href not in url_set:
                new_urls.add(href)

    for crawled_url in new_urls:
        yield crawled_url


async def process_sub_topics(driver):
    print(f"Url: {driver.current_url} is loaded")

    show_more = 0
    fail = 0

    try:
        while show_more == 0:  # Limit "Show More" button clicks to 5 times
            try:
                div = driver.find_element(By.CLASS_NAME, 'search-pagination')
                button_element = div.find_element(By.TAG_NAME, 'button')
                button_element.click()

                time.sleep(5)

                prev_height = driver.execute_script("return document.body.scrollHeight")

                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == prev_height:
                        break
                    prev_height = new_height

                time.sleep(5)
                show_more += 1
                print(f"Times show more clicked: {show_more}\n \n \n")

                async for crawled_url in scrape_urls(driver):
                    print(f"Processing URL: {crawled_url}")
                    url_set.add(crawled_url)
                    yield crawled_url
            except NoSuchElementException as e:
                print(e)
                time.sleep(10)
                fail += 1
                print(f"No button found: fail: {fail}")
                break
    except NoSuchElementException as e:
        print(e)
        time.sleep(10)
        print(f"The loop failed: {fail}")

    # Convert set to a string and append to a file
    set_string = '\n'.join(str(item) if item is not None else '' for item in url_set)
    file_path = './urls.txt'
    with open(file_path, 'a') as file:
        file.write(set_string + '\n')

    print(f"url_set has been written to {file_path} - len {len(url_set)}")


async def crawl(url='https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions'):
    driver = webdriver.Firefox()  # Use the appropriate WebDriver for your browser

    driver.get(url)
    time.sleep(20)

    async for crawled_url in process_sub_topics(driver):
        yield crawled_url

    driver.quit()


def main():
    asyncio.run(crawl())  # Use asyncio.run to run the async function


if __name__ == "__main__":
    main()
