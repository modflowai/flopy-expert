import asyncio
from incremental_processor import IncrementalFloPyProcessor

async def test_incremental():
    processor = IncrementalFloPyProcessor()
    
    # Setup tracking table
    await processor.setup_tracking_table()
    
    # Process just 5 files
    await processor.run(max_files=5)

if __name__ == "__main__":
    asyncio.run(test_incremental())