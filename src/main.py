from dataclasses import asdict, dataclass
import time
from typing import Any, Callable

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Playwright, sync_playwright, Page


SLEEP_BETWEEN_PAGES_S = 10
BASE_URL = "https://www.elibrary.ru"
LOGIN = ""
PASSWORD = ""


@dataclass
class PublicationData:
    number: int
    title: str | None
    authors: str | None
    info: str | None
    url: str | None


def try_or_none(callback: Callable) -> Any | None:
    try:
        return callback()
    except Exception as e:
        print("Error:", e)


def login(page: Page):
    page.goto(BASE_URL)
    page.locator("#login").click()
    page.locator("#login").fill(LOGIN)
    page.get_by_role(
        "cell", name="Имя пользователя  или адрес эл. почты:", exact=True
    ).click()
    page.locator("#password").click()
    page.locator("#password").fill(PASSWORD)
    page.get_by_role("checkbox").check()
    page.get_by_text("Вход", exact=True).click()


def save_publications_info(publications_info: list[PublicationData]):
    if publications_info:
        df = pd.DataFrame([asdict(item) for item in publications_info])
        df.to_csv(
            f"collected_data/data{publications_info[0].number}-{publications_info[-1].number}.csv"
        )


def parse(page: Page, org_id: int, current_page: int):
    publications_info: list[PublicationData] = []

    while True:
        html = page.content()
        bs = BeautifulSoup(html, "html.parser")

        if "page_captcha" in page.url:
            input("Пройди капчу! (как пройдешь жми ENTER)")
            time.sleep(SLEEP_BETWEEN_PAGES_S)
            break

        # has_next_page = bs.find("a", string="Следующая страница")
        # if not has_next_page:
        #     print("Нет следующей страницы! Останавливаюсь")
        #     break

        print(f"Записываю страницу {current_page} ...")

        publications = bs.select("table#restab tr[id^=arw]")
        publications_info.extend(
            [
                PublicationData(
                    int(number.replace(".", "")),
                    (title or "").strip(),
                    (authors or "").strip(),
                    (info or "").strip(),
                    url,
                )
                for number, title, authors, info, url in zip(
                    [
                        try_or_none(lambda: pub.select_one("b").text)
                        for pub in publications
                    ],
                    [
                        try_or_none(lambda: pub.select_one("span").text)
                        for pub in publications
                    ],
                    [
                        try_or_none(lambda: pub.select_one("i").text)
                        for pub in publications
                    ],
                    [
                        try_or_none(lambda: pub.select("font")[-1].text)
                        for pub in publications
                    ],
                    [
                        try_or_none(lambda: BASE_URL + pub.select_one("a")["href"])
                        for pub in publications
                    ],
                )
            ]
        )

        current_page += 1

        if current_page % 10 == 0:
            save_publications_info(publications_info)

        page.get_by_role("link", name="Следующая страница").click()
        time.sleep(SLEEP_BETWEEN_PAGES_S)

    # ---------------------
    print(f"Закончил на странице {current_page}, продолжаю парсить")

    save_publications_info(publications_info)

    if current_page != 150:
        parse(page, org_id, current_page)


def run(playwright: Playwright, org_id: int, start_page: int) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    login(page)

    page.goto(f"https://elibrary.ru/org_items.asp?orgsid={org_id}&pagenum={start_page}")

    parse(page, org_id, start_page)

    context.close()
    browser.close()


try:
    with sync_playwright() as playwright:
        run(playwright, org_id=1193, start_page=1)
except Exception as e:
    ...
