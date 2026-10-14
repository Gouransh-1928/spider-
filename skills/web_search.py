"""
SPIDER — Deep Web Search
Uses DuckDuckGo (no API key) + Playwright for full page scraping.
Supports job search, shopping, and general knowledge queries.
"""
import re
from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS
from loguru import logger

from config.loader import CONFIG


class WebSearch:
    """
    Web search and scraping skill for SPIDER.
    Primary: DuckDuckGo search (no API key needed)
    Extended: Playwright for deep scraping of specific sites
    """

    def __init__(self):
        self.max_results = CONFIG["search"]["max_results"]
        self.timeout = CONFIG["search"]["timeout"]

    def handle(self, user_input: str) -> str:
        """Parse user intent and perform the appropriate search."""
        text = user_input.lower()

        # Detect job search
        if any(word in text for word in ["job", "vacancy", "hiring", "career", "opening"]):
            query = self._extract_query(user_input, ["search for", "find", "look for", "show me"])
            results = self.search_jobs(query or user_input)
            return self._format_results(results, "job")

        # Detect shopping
        elif any(word in text for word in ["buy", "price", "shop", "order", "amazon", "flipkart", "product"]):
            query = self._extract_query(user_input, ["buy", "price of", "find", "search for"])
            results = self.search_shopping(query or user_input)
            return self._format_results(results, "shopping")

        # General search
        else:
            query = self._extract_query(user_input, ["search for", "find", "what is", "who is", "tell me about", "google"])
            results = self.search_general(query or user_input)
            return self._format_results(results, "general")

    def search_general(self, query: str) -> List[Dict[str, str]]:
        """Perform a general web search."""
        logger.info(f"Searching web for: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=self.max_results,
                    region="in-en",
                ))
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []

    def search_jobs(self, query: str) -> List[Dict[str, str]]:
        """Search for job listings."""
        full_query = f"site:linkedin.com OR site:naukri.com OR site:indeed.in {query} jobs 2024 2025"
        logger.info(f"Searching jobs: {full_query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(full_query, max_results=self.max_results))
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            logger.error(f"Job search error: {e}")
            return []

    def search_shopping(self, query: str) -> List[Dict[str, str]]:
        """Search for shopping results."""
        full_query = f"site:amazon.in OR site:flipkart.com {query} price buy"
        logger.info(f"Searching shopping: {full_query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(full_query, max_results=self.max_results))
            return [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
        except Exception as e:
            logger.error(f"Shopping search error: {e}")
            return []

    def get_page_content(self, url: str) -> Optional[str]:
        """Scrape a page and return its text content (uses Playwright)."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.timeout * 1000)
                content = page.inner_text("body")
                browser.close()
                return content[:5000]  # Return first 5000 chars
        except Exception as e:
            logger.error(f"Page scrape error for {url}: {e}")
            return None

    def _extract_query(self, text: str, prefixes: List[str]) -> str:
        """Extract the actual search query from a command."""
        text_lower = text.lower()
        for prefix in prefixes:
            if prefix in text_lower:
                idx = text_lower.find(prefix) + len(prefix)
                return text[idx:].strip(" ?.")
        return text.strip()

    def _format_results(self, results: List[Dict], result_type: str) -> str:
        """Format search results as a readable string for SPIDER to narrate."""
        if not results:
            return f"I couldn't find any {result_type} results for that query."

        lines = [f"Here are the top {result_type} results I found:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   {r['snippet'][:200]}")
            lines.append(f"   Link: {r['url']}\n")

        return "\n".join(lines)
