import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_single_doc():
    firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json"
    }
    
    # Test with WEL package documentation
    url = "https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html"
    
    async with aiohttp.ClientSession() as session:
        scrape_url = "https://api.firecrawl.dev/v1/scrape"
        data = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True
        }
        
        async with session.post(scrape_url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                if result.get('success'):
                    markdown = result['data']['markdown']
                    print(f"Got {len(markdown)} characters")
                    print("\nFirst 1000 characters:")
                    print(markdown[:1000])
                    
                    # Save for inspection
                    with open('wel_docs.md', 'w') as f:
                        f.write(markdown)
                    print("\nSaved to wel_docs.md")

if __name__ == "__main__":
    asyncio.run(test_single_doc())