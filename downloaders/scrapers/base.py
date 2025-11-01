from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class BaseScraper:
    def __init__(self, headless=True):
        self.driver = None
        self.headless = headless
        self._init_driver()

    def _init_driver(self):
        if self.driver:
            return
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,720")
        self.driver = webdriver.Chrome(options=options)

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __del__(self):
        self.close()