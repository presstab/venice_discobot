import os
import sys
import asyncio
import dotenv
from pathlib import Path

# Add parent directory to path so we can import the src module
sys.path.append(str(Path(__file__).parent.parent))
from src.venice_api import VeniceAPI

def test_venice_api():
    """
    Test the VeniceAPI class by loading the API key from .env,
    creating an instance, and asking a question about staking rewards.
    """
    # Load environment variables from .env file
    dotenv.load_dotenv()
    
    # Get API key from environment variables
    api_key = os.getenv("VENICE_API_KEY")
    
    if not api_key:
        raise EnvironmentError("VENICE_API_KEY not found in .env file")
    
    # Create an instance of VeniceAPI
    venice_api = VeniceAPI(api_key)
    
    # Define the question
    question = "do my rewards from staking have to be claimed within a certain period?"

    # Run the async function to get an answer
    answer = asyncio.run(venice_api.get_answer(question))
    
    # Print the answer
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # Verify that we got a non-empty response
    assert answer, "No answer was returned from the API"
    print("Test completed successfully!")

if __name__ == "__main__":
    test_venice_api()