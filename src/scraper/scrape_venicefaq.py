import requests
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import json
import ftfy
import os
from pathlib import Path

# Define the FAQ page URL
FAQ_URL = "https://venice.ai/faqs"

async def scrape_venice_faq(url, cutoff_phrase=""):
    """
    Asynchronously scrape the Venice.ai FAQ page and return parsed HTML.
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error: Unable to fetch page (Status Code: {response.status})")
                return None

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)

            if cutoff_phrase != "":
                index = text.find(cutoff_phrase)
                if index != -1:
                    text = text[:index + len(cutoff_phrase)]
                else:
                    print("cutoff not found")

            # if cutoff_phrase in text:
            #     print("found")

            print(f"text len: {len(text)}")

if __name__ == "__main__":
    asyncio.run(scrape_venice_faq(FAQ_URL, "AI companies can’t and won’t."))