import asyncio
import aiohttp
import json

async def test_firecrawl():
    api_key = "fc-cf70e3a8cd8b4bc595461be67e7b1a79"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Scrape the main code documentation page
    print("Testing Firecrawl scrape...")
    async with aiohttp.ClientSession() as session:
        scrape_url = "https://api.firecrawl.dev/v1/scrape"
        data = {
            "url": "https://flopy.readthedocs.io/en/stable/code.html",
            "formats": ["markdown"],
            "onlyMainContent": True
        }
        
        async with session.post(scrape_url, headers=headers, json=data) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                if result.get('success'):
                    markdown = result['data']['markdown']
                    print(f"Success! Got {len(markdown)} characters")
                    print("\nFirst 500 characters:")
                    print(markdown[:500])
                    
                    # Save to file for inspection
                    with open('flopy_code_docs.md', 'w') as f:
                        f.write(markdown)
                    print("\nFull content saved to flopy_code_docs.md")
                else:
                    print(f"API returned success=false: {result}")
            else:
                error = await response.text()
                print(f"Error: {error}")

if __name__ == "__main__":
    asyncio.run(test_firecrawl())