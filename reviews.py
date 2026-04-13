import csv
import os

from dateutil import parser as dateparser
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from selectorlib import Extractor


FIELDS = [
    "title",
    "content",
    "date",
    "variant",
    "images",
    "verified",
    "author",
    "rating",
    "product",
    "url",
]

CAPTCHA_MARKERS = (
    "Enter the characters you see below",
    "Type the characters you see in this image",
    "api-services-support@amazon.com",
)

extractor = Extractor.from_yaml_file("selectors.yml")


def scrape_page(context, url):
    print("Opening %s" % url)
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        html = page.content()
        if any(marker in html for marker in CAPTCHA_MARKERS):
            print("Captcha/anti-bot detected for %s" % url)
            return None
        return extractor.extract(html)
    except PlaywrightTimeoutError:
        print("Timeout while loading %s" % url)
        return None
    finally:
        page.close()


def normalize_review(review, product_title, url):
    review["product"] = product_title or ""
    review["url"] = url

    verified_text = review.get("verified", "")
    review["verified"] = "Yes" if "Verified Purchase" in verified_text else "No"

    rating = review.get("rating", "")
    if rating:
        review["rating"] = rating.split(" out of")[0]

    date_text = review.get("date", "")
    if date_text and "on " in date_text:
        date_posted = date_text.split("on ")[-1]
        review["date"] = dateparser.parse(date_posted).strftime("%d %b %Y")

    images = review.get("images")
    if images:
        review["images"] = "\n".join(images)

    return review


def main():
    headless = os.getenv("HEADLESS", "true").lower() != "false"

    with open("urls.txt", "r", encoding="utf-8") as urllist, open("data.csv", "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        urls = [line.strip() for line in urllist if line.strip()]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, slow_mo=100)
            context = browser.new_context(
                locale="en-US",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 900},
            )

            for url in urls:
                data = scrape_page(context, url)
                reviews = (data or {}).get("reviews") or []
                if not reviews:
                    print("No reviews parsed for %s" % url)
                    continue

                product_title = data.get("product_title", "")
                for review in reviews:
                    writer.writerow(normalize_review(review, product_title, url))

            context.close()
            browser.close()


if __name__ == "__main__":
    main()
    