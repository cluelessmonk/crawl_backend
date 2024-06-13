import asyncio
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

async def scrape_urls(driver):
    url_elements = driver.find_elements(By.TAG_NAME, 'a')
    new_urls = set()

    for url_element in url_elements:
        url = url_element.get_attribute('href')
        if url and url.startswith('https://careers.oracle.com/jobs/#en/sites/jobsearch/job'):
            new_urls.add(url)

    return new_urls

async def process_sub_topics(driver):
    print(f"Url: {driver.current_url} is loaded")

    urls = set()
    show_more = 0
    fail = 0

    try:
        while show_more < 1:
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
                print(f"Times show more clicked: {show_more}")

                new_urls = await scrape_urls(driver)
                urls.update(new_urls)
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

    return urls

async def crawl(url='https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions'):
    driver = webdriver.Firefox()  # Use the appropriate WebDriver for your browser
    driver.get(url)
    time.sleep(60)

    urls = await process_sub_topics(driver)
    driver.quit()
    return urls

def main():
    base_url = "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions"
    urls = asyncio.run(crawl(base_url))

    # Save the URLs to a text file
    file_path = './oracle_job_urls.txt'
    with open(file_path, 'w') as file:
        for url in urls:
            file.write(url + '\n')

    print(f"URLs have been saved to {file_path} - Total URLs: {len(urls)}")

if __name__ == "__main__":
    main()
