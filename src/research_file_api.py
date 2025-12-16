from .zsxq_client import ZSXQClient
from loguru import logger

def test_file_api():
    client = ZSXQClient()
    
    # You need a known file_id and group_id to test this
    # Please replace these with real IDs found in your logs or browser
    TEST_FILE_ID = "REPLACE_WITH_REAL_FILE_ID" 
    TEST_GROUP_ID = "REPLACE_WITH_REAL_GROUP_ID"
    
    if TEST_FILE_ID == "REPLACE_WITH_REAL_FILE_ID":
        logger.warning("Please edit this script and provide a valid TEST_FILE_ID and TEST_GROUP_ID to run the research.")
        return

    # Potential API Patterns to test
    patterns = [
        f"https://api.zsxq.com/v2/files/{TEST_FILE_ID}",
        f"https://api.zsxq.com/v2/groups/{TEST_GROUP_ID}/files/{TEST_FILE_ID}",
        f"https://api.zsxq.com/v1/files/{TEST_FILE_ID}/download_url",
    ]
    
    for url in patterns:
        logger.info(f"Testing URL: {url}")
        try:
            resp = client.session.get(url)
            logger.info(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                logger.success(f"Response: {resp.text[:500]}")
                break
            else:
                logger.warning(f"Failed: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_file_api()
