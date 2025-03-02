import aiohttp
import json

class VeniceAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.venice.ai"  # Replace with actual API URL
        
    async def get_answer(self, question):
        """
        Queries the Venice AI API to get an answer based on website information
        
        Args:
            question: The user's question
            
        Returns:
            The answer from Venice AI
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "question": question,
            "source": "discord_bot"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/query", 
                headers=headers, 
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("answer", "No answer found")
                else:
                    error_text = await response.text()
                    raise Exception(f"API error: {response.status} - {error_text}")