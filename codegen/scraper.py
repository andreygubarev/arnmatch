# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4"]
# ///

import logging
import re
from urllib.parse import urljoin

import joblib

log = logging.getLogger(__name__)
import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html"


class AWSScraper:
    def __init__(self, cache_dir: str = ".cache"):
        self._memory = joblib.Memory(cache_dir, verbose=0)
        self._fetch_cached = self._memory.cache(self._fetch)

    def _fetch(self, url: str) -> str:
        r = requests.get(url)
        r.raise_for_status()
        return r.text

    def _soup(self, url: str) -> BeautifulSoup:
        html = self._fetch_cached(url)
        return BeautifulSoup(html, "html.parser")

    def get_services(self) -> list[dict]:
        """Fetch list of AWS services from index page."""
        soup = self._soup(INDEX_URL)
        highlights = soup.find("div", class_="highlights")

        services = []
        for li in highlights.find_all("li"):
            link = li.find("a")
            if not link:
                raise ValueError("No link found in list item")

            name = link.get_text(strip=True)
            if not name:
                raise ValueError("Link has no text")

            href = link.get("href", "")
            if not href:
                raise ValueError("Link has no href")

            slug = href.removeprefix("./list_").removesuffix(".html")
            absolute_url = urljoin(INDEX_URL, href)
            services.append({"name": name, "href": absolute_url, "slug": slug})

        log.info(f"Found {len(services)} services")
        return services

    def get_resources(self, url: str) -> list[dict]:
        """Fetch resource types and ARN patterns from a service page."""
        soup = self._soup(url)

        # Extract service prefix
        prefix_match = soup.find(string=re.compile(r"service prefix:"))
        if not prefix_match:
            return []

        prefix_code = prefix_match.find_next("code", class_="code")
        if not prefix_code:
            return []
        service = prefix_code.get_text(strip=True)

        # Find resource types table
        resources_heading = soup.find("h2", id=re.compile(r"-resources-for-iam-policies$"))
        if not resources_heading:
            return []

        table = resources_heading.find_next("table")
        if not table:
            return []

        known_resources = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # First cell: resource type name
            resource_cell = cells[0]
            link = resource_cell.find("a")
            resource_type = link.get_text(strip=True) if link else resource_cell.get_text(strip=True)
            if not resource_type:
                continue

            # Second cell: ARN pattern
            arn_cell = cells[1]
            code = arn_cell.find("code", class_="code")
            if not code:
                continue
            arn_pattern = code.get_text(strip=True)

            known_resources.append({
                "service": service,
                "resource_type": resource_type,
                "arn_pattern": arn_pattern,
            })

        log.info(f"{service}: {len(known_resources)} known resources")
        return known_resources


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    scraper = AWSScraper()
    services = scraper.get_services()

    known_resources = []
    for svc in services:
        resources = scraper.get_resources(svc["href"])
        known_resources.extend(resources)

    log.info(f"Total: {len(known_resources)} known resources")
