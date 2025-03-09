import aiohttp


async def get_price_data():
    # Make a request to CoinGecko API
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.coingecko.com/api/v3/coins/venice-token") as response:
            if response.status != 200:
                print(f"Error: Unable to fetch price data (Status Code: {response.status})")
                return None

            # Get the raw JSON response
            data = await response.json()
            price_data = {
                'market_cap_rank': data['market_cap_rank'],
                'market_cap': data['market_data']['market_cap']['usd'],
                'current_price': data['market_data']['current_price']['usd'],
                'all_time_high': data['market_data']['ath']['usd'],
                'all_time_high_date': data['market_data']['ath_date']['usd'],
                'all_time_low': data['market_data']['atl']['usd'],
                'all_time_low_date': data['market_data']['atl_date']['usd'],
                'fully_diluted_valuation': data['market_data']['fully_diluted_valuation']['usd'],
                'market_cap_fdv_ratio': data['market_data']['market_cap_fdv_ratio'],
                'volume_24hr': data['market_data']['total_volume']['usd'],
                '24hr_high': data['market_data']['high_24h']['usd'],
                '24hr_low': data['market_data']['low_24h']['usd'],
                'price_change_percent_24hr': data['market_data']['price_change_percentage_24h'],
                'price_change_percent_7d': data['market_data']['price_change_percentage_7d'],
                'price_change_percent_14d': data['market_data']['price_change_percentage_14d'],
                'price_change_percent_30d': data['market_data']['price_change_percentage_30d'],
                'price_change_percent_60d': data['market_data']['price_change_percentage_60d'],
                'price_change_percent_200d': data['market_data']['price_change_percentage_200d'],
                'price_change_percent_1y': data['market_data']['price_change_percentage_1y'],
                'total_supply': data['market_data']['total_supply'],
                'circulating_supply': data['market_data']['circulating_supply']
            }

            # replace 0% change because coin is new
            price_data['price_change_percent_60d'] = price_data['price_change_percent_60d'] or 'n/a'
            price_data['price_change_percent_200d'] = price_data['price_change_percent_200d'] or 'n/a'
            price_data['price_change_percent_1y'] = price_data['price_change_percent_1y'] or 'n/a'

            return price_data
