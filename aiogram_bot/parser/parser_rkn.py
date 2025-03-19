import os
import logging
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

BASE_URL = 'https://reestr.rublacklist.net/ru/'
OUTPUT_FILE = '../file_parser/urls_to_check.txt'
logging.basicConfig(level=logging.INFO)


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=chrome_options)


def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc or parsed.path.split('/')[0]


def clean_url(url_text):
    url = url_text.strip()
    if not url:
        return None
    parsed_url = urlparse(url)
    domain = parsed_url.netloc or parsed_url.path.split('/')[0]
    if domain.startswith('www.'):
        domain = domain[4:]
    if domain.startswith('*.'):
        domain = domain[2:]
    blocked_tlds = {'ru', 'com', 'uz', 'by', 'us', 'ua', 'kz'}
    if domain.split('.')[-1] in blocked_tlds:
        return None
    return domain


def get_sites_from_page(driver):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    elements = soup.select('div.table_td.td_site a')
    return [clean_url(el.text) for el in elements if el.text.strip()]


def save_urls_to_file(urls, filename):
    unique_urls = list(filter(None, set(urls)))
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(unique_urls))
    return len(unique_urls)


def search_site(query, max_pages=10):
    driver = get_driver()
    try:
        driver.get(BASE_URL)

        # Ожидание полной загрузки страницы
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Заполнение поисковой формы
        search_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.NAME, "q"))
        )
        search_input.clear()
        search_input.send_keys(query)

        # Клик по кнопке поиска с повторными попытками
        for _ in range(3):
            try:
                search_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Найти')]"))
                )
                driver.execute_script("arguments[0].click();", search_button)
                break
            except StaleElementReferenceException:
                driver.refresh()
                continue

        # Выбор статуса
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "selectStatus"))
        )
        Select(driver.find_element(By.ID, "selectStatus")).select_by_value("2")

        all_sites = []
        current_page = 1

        while current_page <= max_pages:
            try:
                # Ожидание загрузки данных
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "table_td"))
                )

                # Сбор данных и фильтрация
                page_sites = [
                    domain for domain in get_sites_from_page(driver)
                    if domain and query.lower() in domain.lower()
                ]

                all_sites.extend(page_sites)
                logging.info(f"Страница {current_page}: найдено {len(page_sites)} подходящих доменов")

                # Поиск кнопки "Далее"
                next_buttons = driver.find_elements(By.CSS_SELECTOR, "a.btn_next:not(.disabled)")
                if not next_buttons:
                    logging.info("Кнопка следующей страницы не найдена")
                    break

                # Скролл и клик с повторными попытками
                for attempt in range(3):
                    try:
                        next_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_next:not(.disabled)"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                        time.sleep(1)
                        next_btn.click()

                        WebDriverWait(driver, 30).until(
                            EC.staleness_of(next_btn)
                        )
                        current_page += 1
                        break
                    except StaleElementReferenceException:
                        if attempt == 2:
                            raise
                        driver.refresh()
                        time.sleep(2)
                        continue

            except Exception as e:
                logging.error(f"Ошибка: {str(e)}")
                break

    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
    finally:
        driver.quit()

    # Дополнительная фильтрация результатов
    filtered_domains = [
        domain for domain in all_sites
        if domain and query.lower() in domain.lower()
    ]

    save_urls_to_file(filtered_domains, OUTPUT_FILE)
    return len(filtered_domains)
