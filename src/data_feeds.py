from bs4 import BeautifulSoup
import aiohttp
import re
import json
import time
import os
from datetime import datetime


async def get_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error: Unable to fetch page (Status Code: {response.status})\n -- URL: {url}")
                return None

            return await response.text()


class DataAugmenter:
    def __init__(self, scrape_list=None, guild_id=None):
        self.cache = None
        self.last_update_time = None
        self.api_url = "https://venice.ai/faqs"
        self.scrap_list = scrape_list or []
        self.guild_id = guild_id  # Store guild_id for context-specific loading
        self.custom_augment = self._load_custom_context()
        print(f"DataAugmenter initialized for guild: {guild_id}, with {len(self.scrap_list)} URLs and custom context: {len(self.custom_augment)} items")
    
    def _load_custom_context(self):
        """
        Load custom context from JSON file
        If guild_id is set, only returns context for that guild
        Otherwise returns empty list
        """
        if self.guild_id is None:
            print("No guild_id provided to DataAugmenter, no custom context will be loaded")
            return []
            
        try:
            with open("config/custom_context.json", "r") as f:
                data = json.load(f)
                
                # Check if we have the new guild-specific format
                if isinstance(data, dict):
                    guild_id_str = str(self.guild_id)
                    if guild_id_str in data and "context_list" in data[guild_id_str]:
                        if isinstance(data[guild_id_str]["context_list"], list):
                            return data[guild_id_str]["context_list"]
                
                # Old format compatibility - only if guild_id matches or no guild_id was specified
                elif "context_list" in data and isinstance(data["context_list"], list):
                    return data["context_list"]
                
                # No context found for this guild
                return []
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty list if file doesn't exist or is invalid
            return []
    
    async def scrape_all(self):
        """
        Scrapes all data sources and caches the results.
        Updates the last update time.
        """
        if self.cache is None:
            self.cache = await self._fetch_all_data()
            self.last_update_time = datetime.now()
        return self.cache
    
    async def refresh(self):
        """
        Force refresh the cached data.
        """
        guild_info = f"for guild {self.guild_id}" if self.guild_id else ""
        print(f"Refreshing DataAugmenter cache {guild_info}...")
        start_time = time.time()
        self.custom_augment = self._load_custom_context()  # Reload custom context
        self.cache = await self._fetch_all_data()
        self.last_update_time = datetime.now()
        elapsed = time.time() - start_time
        print(f"DataAugmenter cache refreshed {guild_info} in {elapsed:.2f}s")
        return self.cache
    
    async def get_data(self, max_age_seconds=3600):
        """
        Get cached data, refreshing if older than max_age_seconds.
        """
        if self.cache is None or self.last_update_time is None:
            print("No cache found, scraping all data...")
            return await self.scrape_all()
        
        current_time = datetime.now()
        age = (current_time - self.last_update_time).total_seconds()
        
        if age > max_age_seconds:
            print(f"Cache is {age:.2f}s old (max age: {max_age_seconds}s), refreshing...")
            return await self.refresh()
        
        print(f"Using cached data ({age:.2f}s old)")
        return self.cache
    
    async def _fetch_all_data(self):
        """
        Internal method to fetch all data from sources.
        """
        print("Fetching data from all sources...")
        start_time = time.time()
        
        faq_start = time.time()
        augmented_text = await self.scrape_venice_faq()
        faq_time = time.time() - faq_start
        print(f"Venice FAQ data fetched in {faq_time:.2f}s")
        
        api_start = time.time()
        api_docs = await self.scrape_api_docs()
        api_time = time.time() - api_start
        print(f"API docs fetched in {api_time:.2f}s ({len(self.scrap_list)} URLs)")
        
        augmented_text += api_docs
        
        # Add custom context if available
        if self.custom_augment and isinstance(self.custom_augment, list):
            custom_text = "\n\nIMPORTANT CUSTOM CONTEXT:\n"
            for item in self.custom_augment:
                custom_text += f"- {item}\n"
            augmented_text += custom_text
            print(f"Added custom context with {len(self.custom_augment)} items")
        
        total_time = time.time() - start_time
        print(f"All data fetched in {total_time:.2f}s")
        return augmented_text

    async def _scrape(self):
        html = await get_url(self.api_url)
        soup = BeautifulSoup(html, "html.parser")

        # Find and store the desired script content before removing scripts
        desired_script = soup.find("script", text=lambda t: t and "Frequently Asked Questions" in t)
        if desired_script:
            faq_content = desired_script.get_text()
            # Assume faq_content is the string you extracted
            # This regex finds the first JSON-like block (from the first '{' to the last '}')
            json_match = re.search(r'({.*})', faq_content, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                faq_data = json_str.replace('\\"', '"')
                return faq_data

    async def scrape_venice_faq(self):
        """
        Asynchronously scrape the Venice.ai FAQ page and return parsed HTML.
        """
        faq_data = await self._scrape()

        faq_data = faq_data.replace('\\\"', '\"')
        # Add this to your function to debug the JSON parsing error
        faq_data_dict = json.loads(faq_data)

        def flatten_text_fields(obj):
            if isinstance(obj, dict):
                return {k: flatten_text_fields(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                if all(isinstance(i, str) for i in obj):
                    return ' '.join(obj)
                return [flatten_text_fields(i) for i in obj]
            else:
                return obj

        flattened = flatten_text_fields(faq_data_dict)

        result = ""
        if "faqItems" not in flattened:
            return ""

        for faqItem in flattened['faqItems']:
            question = faqItem.get("question")
            if not question:
                print(f"*** no question: {faqItem}")
            if question:
                result += f"\nQuestion: {question} Answer: "
                for item in faqItem["answer"]["json"]["content"]:
                    if "content" in item:
                        content_list = item["content"]
                        for c in content_list:
                            if "text" in c:
                                result += f" {c['text']}"
                            elif "type" in c and c["type"] == "listItem":
                                list_items = c["content"]
                                for list_item in list_items:
                                    if "content" in list_item:
                                        for c2 in list_item["content"]:
                                            if "text" in c2:
                                                result += f" {c2['text']}"

        if "faqCategories" not in flattened:
            return result
        
        for category in flattened['faqCategories']:
            if "questions" in category:
                items = category["questions"]["items"]
                for item in items:
                    if "question" in item:
                        result += f"\nQuestion: {item['question']} Answer: "
                        for it in item["answer"]["json"]["content"]:
                            if "content" in it:
                                content_list = it["content"]
                                for c in content_list:
                                    if "text" in c:
                                        result += f" {c['text']}"
                                    elif "type" in c and c["type"] == "listItem":
                                        list_items = c["content"]
                                        for list_item in list_items:
                                            if "content" in list_item:
                                                for c2 in list_item["content"]:
                                                    if "text" in c2:
                                                        result += f" {c2['text']}"

        return result

    async def scrape_api_docs(self):
        augment_text = ""
        for url in self.scrap_list:
            response = await get_url(url)
            if response is not None:
                augment_text += f"File: {response}\n"

        return augment_text
