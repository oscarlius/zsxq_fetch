import time
from playwright.sync_api import sync_playwright
from loguru import logger
from .config import AUTH_FILE_PATH

def login_and_save_state():
    """
    Launches a browser for the user to login to knowledge planet.
    Saves the storage state (cookies, local storage) to a file upon successful login.
    """
    logger.info("Starting Playwright for authentication...")
    
    with sync_playwright() as p:
        # Launch headed browser so user can see and scan QR code
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        login_url = "https://wx.zsxq.com/dweb2/login"
        logger.info(f"Navigating to {login_url}")
        page.goto(login_url)
        
        logger.info("Please scan the QR code or login via phone in the browser window.")
        logger.info("Waiting for login to complete (detecting URL change to index)...")
        
        try:
            # Wait for URL to switch to the main feed/index page
            # Usually redirects to https://wx.zsxq.com/dweb2/index/group/...
            page.wait_for_url("**/dweb2/index**", timeout=300000) # 5 minutes timeout for user to login
            
            logger.info("Login detected! Saving authentication state...")
            
            # Ensure the directory for auth file exists
            AUTH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            context.storage_state(path=str(AUTH_FILE_PATH))
            logger.info(f"Authentication state saved to: {AUTH_FILE_PATH}")
            logger.success("You can now run the crawler component.")
            
        except Exception as e:
            logger.error(f"Login timed out or failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    login_and_save_state()
