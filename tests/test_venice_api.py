import os
import sys
import asyncio
import dotenv
from pathlib import Path
from bs4 import BeautifulSoup
import aiohttp
import re
import json
from pprint import pprint

# Add parent directory to path so we can import the src module
sys.path.append(str(Path(__file__).parent.parent))
from src.venice_api import VeniceAPI
from src.price import get_price_data
from src.data_feeds import DataAugmenter

async def scrape_venice_faq(url, cutoff_before_phrase="", cutoff_after_phrase=""):
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

            # Find and store the desired script content before removing scripts
            desired_script = soup.find("script", text=lambda t: t and "Frequently Asked Questions" in t)
            if desired_script:
                faq_content = desired_script.get_text()
                # Assume faq_content is the string you extracted
                # This regex finds the first JSON-like block (from the first '{' to the last '}')
                json_match = re.search(r'({.*})', faq_content, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1)
                    cleaned_json_str = json_str.replace('\\"', '"')
                    print(f"json_str {cleaned_json_str}")
                    try:
                        faq_json = json.loads(cleaned_json_str)
                    except json.JSONDecodeError as e:
                        print("Error decoding JSON:", e)
                    else:
                        # Pretty-print the JSON
                        formatted_json = json.dumps(faq_json, indent=4)
                        print(formatted_json)
                # with open("raw.txt", "w", encoding="utf-8") as f:
                #     f.write(faq_content)

            text = soup.get_text(separator="\n", strip=True)


            #cut out anything before the phrase match
            if cutoff_before_phrase != "":
                index = text.find(cutoff_before_phrase)
                if index != -1:
                    text = text[index:]

            #cut out anything after the phrase match
            if cutoff_after_phrase != "":
                index = text.find(cutoff_after_phrase)
                if index != -1:
                    text = text[:index + len(cutoff_after_phrase)]

            return text

async def get_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error: Unable to fetch page (Status Code: {response.status})\n -- URL: {url}")
                return None

            return await response.text()

async def scrape_api_docs():
    dotenv.load_dotenv()

    # Get API key from environment variables
    api_key = os.getenv("VENICE_API_KEY")

    if not api_key:
        raise EnvironmentError("VENICE_API_KEY not found in .env file")

    url_list = [
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/ai-agents.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/generating-api-key-agent.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/generating-api-key.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/integrations.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/postman.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/guides/structured-responses.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/about-venice.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/getting-started.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/pricing.mdx",
        "https://raw.githubusercontent.com/veniceai/api-docs/main/welcome/privacy.mdx",
        "https://api.venice.ai/doc/api/swagger.yaml"
    ]


    augment_text = ""
    for url in url_list:
        response = await get_url(url)
        if response is not None:
            augment_text += response

    venice_api = VeniceAPI(api_key)
    venice_api.model = "llama-3.3-70b"

    # Define the question
    question = "is the koroko voice function updated in the api somewhere? I can't find how to callit in the docs. or postman"

    # Run the async function to get an answer
    answer = await venice_api.get_answer(question, topic="Venice AI", context_file=None, raw_context=augment_text)

    # Print the answer
    print(f"Question: {question}")
    print(f"Answer: {answer['answer']}")
    for citation in answer['citations']:
        print(citation['url'])

    # Verify that we got a non-empty response
    assert answer, "No answer was returned from the API"
    print("Test completed successfully!")


async def test_price():
    price_data = await get_price_data()
    print(price_data)

async def test_venice_api():
    """
    Test the VeniceAPI class by loading the API key from .env,
    creating an instance, and asking a question about staking rewards.
    """

    await scrape_venice_faq("https://venice.ai/faqs")
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    # Get API key from environment variables
    api_key = os.getenv("VENICE_API_KEY")
    
    if not api_key:
        raise EnvironmentError("VENICE_API_KEY not found in .env file")
    
    # Create an instance of VeniceAPI
    venice_api = VeniceAPI(api_key)
    venice_api.model = "llama-3.3-70b"
    #venice_api.model = "deepseek-r1-671b"
    #venice_api.model = "dolphin-2.9.2-qwen2-72b:enable_web_search=off"

    # Define the question
    question = "do my rewards from staking have to be claimed within a certain period?"

    # Run the async function to get an answer
    answer = asyncio.run(venice_api.get_answer(question, topic="Venice AI"))
    
    # Print the answer
    print(f"Question: {question}")
    print(f"Answer: {answer['answer']}")
    for citation in answer['citations']:
        print(citation['url'])

    # Verify that we got a non-empty response
    assert answer, "No answer was returned from the API"
    print("Test completed successfully!")


async def test_data_augmenter():
    """
    Test the DataAugmenter class with FAQ scraping functionality
    """
    print("\n===== Testing DataAugmenter =====")
    
    # Create a test guild ID
    test_guild_id = "123456789"
    
    # Create a DataAugmenter instance with a test guild ID
    # Use an empty scrape list to focus on FAQ scraping
    data_augmenter = DataAugmenter([], test_guild_id)
    
    # Set the API URL to the Venice FAQ page
    data_augmenter.api_url = "https://venice.ai/faqs"
    
    # Test scraping the Venice FAQ page
    print("Scraping Venice FAQ page...")
    faq_data = await data_augmenter.scrape_venice_faq()
    
    # Verify that we got a non-empty response
    assert faq_data, "No data was returned from scraping the FAQ"
    assert len(faq_data) > 100, f"FAQ data seems too short: {len(faq_data)} characters"
    print(faq_data)

    # Test the full data fetch process
    print("\nTesting full data augmentation process...")
    all_data = await data_augmenter.get_data()
    
    # Verify that we got a non-empty response
    assert all_data, "No data was returned from the data augmenter"
    assert len(all_data) > 100, f"Augmented data seems too short: {len(all_data)} characters"
    
    print(f"Successfully fetched augmented data: {len(all_data)} characters")
    
    # Test the refresh functionality
    print("\nTesting refresh functionality...")
    refreshed_data = await data_augmenter.refresh()
    
    # Verify that we got a non-empty response
    assert refreshed_data, "No data was returned after refresh"
    assert len(refreshed_data) > 100, f"Refreshed data seems too short: {len(refreshed_data)} characters"
    
    print(f"Successfully refreshed data: {len(refreshed_data)} characters")
    print("DataAugmenter test completed successfully!")

async def test_guild_specific_context():
    """
    Test the guild-specific context functionality in DataAugmenter
    """
    print("\n===== Testing Guild-Specific Context =====")
    
    # Create two test guild IDs to verify isolation
    guild_id_1 = "111111111"
    guild_id_2 = "222222222"
    
    # Create a temporary custom_context.json file for testing
    temp_context = {
        guild_id_1: {
            "context_list": [
                "Guild 1 context item 1",
                "Guild 1 context item 2"
            ]
        },
        guild_id_2: {
            "context_list": [
                "Guild 2 context item 1",
                "Guild 2 context item 2",
                "Guild 2 context item 3"
            ]
        }
    }
    
    # Save the temporary context to a file
    os.makedirs("config", exist_ok=True)
    with open("config/custom_context.json", "w") as f:
        json.dump(temp_context, f, indent=4)
    
    try:
        # Create DataAugmenter instances for each test guild
        print("Creating DataAugmenter instances for two test guilds...")
        augmenter_1 = DataAugmenter([], guild_id_1)
        augmenter_2 = DataAugmenter([], guild_id_2)
        
        # Verify that each augmenter only loads its own guild's context
        print("Checking context isolation between guilds...")
        
        # Check first guild's context
        custom_context_1 = augmenter_1.custom_augment
        assert len(custom_context_1) == 2, f"Expected 2 context items for guild 1, got {len(custom_context_1)}"
        assert "Guild 1 context item 1" in custom_context_1, "Missing expected context item for guild 1"
        assert "Guild 2 context item 1" not in custom_context_1, "Guild 1 contains context from guild 2"
        
        # Check second guild's context
        custom_context_2 = augmenter_2.custom_augment
        assert len(custom_context_2) == 3, f"Expected 3 context items for guild 2, got {len(custom_context_2)}"
        assert "Guild 2 context item 1" in custom_context_2, "Missing expected context item for guild 2"
        assert "Guild 1 context item 1" not in custom_context_2, "Guild 2 contains context from guild 1"
        
        print("Guild context isolation verified successfully")
        
        # Test that context is included in the augmented data
        print("Testing context inclusion in augmented data...")
        
        # Get augmented data for guild 1
        data_1 = await augmenter_1.get_data()
        assert "Guild 1 context item 1" in data_1, "Guild 1 context not included in augmented data"
        assert "Guild 2 context item 1" not in data_1, "Guild 2 context incorrectly included in guild 1 data"
        
        print("Guild-specific context test completed successfully!")
        
    finally:
        # Clean up the temporary test file
        try:
            os.remove("config/custom_context.json")
            print("Cleaned up temporary test file")
        except:
            pass


if __name__ == "__main__":
    # Choose which test to run by uncommenting one of these lines
    # asyncio.run(scrape_api_docs())
    # asyncio.run(test_venice_api())
    # asyncio.run(test_price())
    # asyncio.run(test_data_augmenter())
    
    # Run both DataAugmenter tests
    asyncio.run(test_data_augmenter())
    asyncio.run(test_guild_specific_context())