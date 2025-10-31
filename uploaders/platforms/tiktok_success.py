"""
Enhance TikTok success validation after clicking Post
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def wait_tiktok_success(driver, timeout=120) -> bool:
    """Wait for signals that upload succeeded: toast, redirect, or specific DOM changes."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            # Toast message
            toast = driver.find_elements(By.XPATH, "//div[contains(., 'posted') or contains(., 'success') or contains(., 'uploaded')]")
            if toast:
                return True
            # Redirect to video manager or similar
            cur = driver.current_url.lower()
            if any(x in cur for x in ["/inbox", "/creator-center", "/video", "/manage"]):
                return True
            # Success icon near button
            ok_icon = driver.find_elements(By.XPATH, "//*[contains(@class, 'success') or contains(@aria-label, 'success')]")
            if ok_icon:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False
