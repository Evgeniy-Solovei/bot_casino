import os
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import Select
from tg_bot import driver

BASE_URL = 'https://reestr.rublacklist.net/ru/'
OUTPUT_FILE = '../file_parser/urls_to_check.txt'


def get_domain(url):
    """Извлекает домен из URL"""
    parsed = urlparse(url)
    return parsed.netloc or parsed.path.split('/')[0]


def clean_url(url_text):
    """Очищает URL и возвращает только домен"""
    url = url_text.replace(' ', '').replace('\n', '')
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
    domain = get_domain(url)
    # Убираем * в начале, если есть
    if domain.startswith('*.'):
        domain = domain[2:]
    # Исключаем домены с определёнными зонами
    blocked_tlds = {'ru', 'com', 'uz', 'by', 'us', 'ua', 'kz'}  # Добавь нужные
    if domain.split('.')[-1] in blocked_tlds:
        return None
    return domain


def get_sites_from_page():
    """Извлекает URL с текущей страницы через BeautifulSoup (быстрее, чем Selenium)"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    elements = soup.select('div.table_td.td_site a')
    return [clean_url(el.text) for el in elements if el.text.strip()]


def save_urls_to_file(urls, filename):
    """Сохраняет уникальные URL в файл"""
    unique_urls = list(filter(None, set(urls)))  # Убираем дубликаты + удаляем None
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(unique_urls))
    return len(unique_urls)  # Возвращаем количество записей


def search_site(query, max_pages=20):
    """Функция поиска сайтов"""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    all_sites = set()
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q"))).send_keys(query)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Найти')]").click()

        Select(WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "selectStatus"))
        )).select_by_value("2")

        for current_page in range(1, max_pages + 1):
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.table_td.td_site')))
            page_sites = get_sites_from_page()
            all_sites.update(page_sites)
            save_urls_to_file(all_sites, OUTPUT_FILE)
            print(f"Страница {current_page}: собрано {len(page_sites)} URL | Всего: {len(all_sites)}")
            next_btn = driver.find_elements(By.CSS_SELECTOR, 'a.btn_next:not(.disabled)')
            if not next_btn:
                break
            next_btn[0].click()

    except Exception as e:
        print(f"Ошибка при поиске: {e}")
    finally:
        save_urls_to_file(all_sites, OUTPUT_FILE)
        print(f"\nСбор завершен. Уникальных доменов: {len(all_sites)}")
