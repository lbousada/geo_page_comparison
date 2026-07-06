import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
LOGIN_URL = "https://www.semrush.com/login/"
SEMRUSH_USERNAME_ENV = "SEMRUSH_USERNAME"
SEMRUSH_PASSWORD_ENV = "SEMRUSH_PASSWORD"
SEMRUSH_USERNAME = ""
SEMRUSH_PASSWORD = ""
ANALYZED_URL = "https://www.coursecompare.ca/best-online-mba-canada"
SEMRUSH_BACKLINKS_URL = "https://www.semrush.com/analytics/backlinks/overview/"
SEARCH_TYPE = "subfolder"
WAIT_SECONDS_AFTER_LOGIN = 5
WAIT_SECONDS_ON_TARGET_PAGE = 5
REFERRING_DOMAINS_COUNT_SELECTOR = (
    '[data-test-flag2-item="domains"] [data-test-flag2-value] [data-ui-name="Link.Text"]'
)


def load_env_file(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_semrush_credentials() -> None:
    global SEMRUSH_USERNAME, SEMRUSH_PASSWORD

    load_env_file()
    SEMRUSH_USERNAME = os.environ.get(SEMRUSH_USERNAME_ENV, "").strip()
    SEMRUSH_PASSWORD = os.environ.get(SEMRUSH_PASSWORD_ENV, "").strip()


load_semrush_credentials()


def build_target_url(analyzed_url: str) -> str:
    parsed_url = urlsplit(analyzed_url.strip())
    if parsed_url.netloc:
        semrush_query = f"{parsed_url.netloc}{parsed_url.path}"
    else:
        semrush_query = parsed_url.path

    encoded_query = quote(semrush_query, safe=".")
    return f"{SEMRUSH_BACKLINKS_URL}?q={encoded_query}&searchType={SEARCH_TYPE}"


def build_driver() -> WebDriver:
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)


def accept_cookie_banner_if_present(driver: WebDriver, wait: WebDriverWait) -> None:
    try:
        allow_all = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".ch2-allow-all-btn"))
        )
        allow_all.click()
    except TimeoutException:
        pass


def get_login_form(driver: WebDriver) -> tuple[WebElement, WebElement] | None:
    try:
        email_input = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "email"))
        )
        password_input = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "password"))
        )
        return email_input, password_input
    except TimeoutException:
        return None


def login(driver: WebDriver) -> None:
    if not SEMRUSH_USERNAME or not SEMRUSH_PASSWORD:
        raise ValueError("Set SEMRUSH_USERNAME and SEMRUSH_PASSWORD in .env before running.")

    wait = WebDriverWait(driver, 20)
    driver.get(LOGIN_URL)
    accept_cookie_banner_if_present(driver, WebDriverWait(driver, 3))

    login_form = get_login_form(driver)
    if login_form is None:
        print("Login form was not shown; continuing with the current browser session.")
        time.sleep(WAIT_SECONDS_AFTER_LOGIN)
        return

    email_input, password_input = login_form

    email_input.clear()
    email_input.send_keys(SEMRUSH_USERNAME)
    password_input.clear()
    password_input.send_keys(SEMRUSH_PASSWORD)

    submit_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test="login-page__btn-login"]'))
    )
    submit_button.click()

    wait.until(lambda current_driver: current_driver.current_url != LOGIN_URL)
    time.sleep(WAIT_SECONDS_AFTER_LOGIN)


def parse_metric_count(raw_count: str) -> int:
    match = re.search(r"\d[\d,]*", raw_count)
    if match is None:
        return 0

    return int(match.group(0).replace(",", ""))


def get_referring_domains_count(driver: WebDriver) -> int:
    try:
        count_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, REFERRING_DOMAINS_COUNT_SELECTOR)
            )
        )
    except TimeoutException:
        return 0

    return parse_metric_count(count_element.text)


def visit_target_page(driver: WebDriver) -> int:
    if not ANALYZED_URL:
        raise ValueError("Set ANALYZED_URL at the top of this script before running.")

    target_url = build_target_url(ANALYZED_URL)
    driver.switch_to.new_window("tab")
    driver.get(target_url)
    time.sleep(WAIT_SECONDS_ON_TARGET_PAGE)
    return get_referring_domains_count(driver)


def main() -> None:
    driver = build_driver()
    try:
        login(driver)
        referring_domains_count = visit_target_page(driver)
        print(f"Referring domains: {referring_domains_count}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
