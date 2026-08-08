import json
import time
import os
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException

# ==================== CONFIGURATION ====================
URL = "https://parvezh4x.gamer.gd/cron.php?key=PARVEZH4x412065"
FETCH_INTERVAL_SECONDS = 60  # how often to fetch data
MAX_LOG_ENTRIES = 100        # limit stored logs to avoid memory bloat
# ======================================================

app = Flask(__name__)

# In-memory log storage (thread-safe)
fetch_logs = []
log_lock = threading.Lock()


def get_chrome_options():
    """Create Chrome options suitable for headless execution, Termux or otherwise."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Termux‑specific tweaks (harmless on other systems)
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    # Allow custom binary path via environment variable (for Termux)
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin
    else:
        # Default Termux fallback (won't break if file doesn't exist)
        for path in ["/data/data/com.termux/files/usr/bin/chromium-browser",
                     "/data/data/com.termux/files/usr/bin/chromium"]:
            if os.path.exists(path):
                chrome_options.binary_location = path
                break

    return chrome_options


def get_driver():
    """Instantiate a Chrome WebDriver with automatic driver management."""
    options = get_chrome_options()

    # Use webdriver-manager to auto-download chromedriver (works on Linux/Windows/macOS)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception:
        # Fallback for Termux: chromedriver must be in PATH or explicitly set
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "chromedriver")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver


def fetch_json_with_browser():
    """
    Perform one fetch using Selenium.
    Returns a dict with keys: timestamp, status ('success' or 'error'),
    data (JSON object or None), message (error string if any).
    """
    driver = None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = {
        "timestamp": timestamp,
        "status": "error",
        "data": None,
        "message": ""
    }

    try:
        driver = get_driver()
        driver.set_page_load_timeout(60)
        driver.get(URL)

        # Wait for JavaScript (e.g., InfinityFree challenge) to complete
        time.sleep(5)

        page_text = driver.find_element(By.TAG_NAME, "body").text
        try:
            json_data = json.loads(page_text)
            result["status"] = "success"
            result["data"] = json_data
            result["message"] = "JSON parsed successfully"
        except json.JSONDecodeError:
            result["message"] = f"Invalid JSON. Response preview: {page_text[:200]}"
            result["data"] = page_text  # store raw text for debugging
    except TimeoutException:
        result["message"] = "Page load timed out (60s)"
    except WebDriverException as e:
        result["message"] = f"WebDriver error: {str(e)}"
    except Exception as e:
        result["message"] = f"Unexpected error: {str(e)}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Append to global log (thread-safe)
    with log_lock:
        fetch_logs.append(result)
        # Keep only the last N entries
        if len(fetch_logs) > MAX_LOG_ENTRIES:
            del fetch_logs[0]

    return result


# ---------- Flask Routes ----------
@app.route("/")
def dashboard():
    """Serve the HTML dashboard showing all fetch logs."""
    # Reverse the list so newest entries appear first
    with log_lock:
        logs = list(reversed(fetch_logs))
    return render_template("index.html", logs=logs)


@app.route("/api/logs")
def api_logs():
    """Return logs as JSON for external consumption."""
    with log_lock:
        logs = list(fetch_logs)
    return jsonify(logs)


# ---------- Scheduler ----------
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=fetch_json_with_browser,
        trigger="interval",
        seconds=FETCH_INTERVAL_SECONDS,
        id="selenium_fetch",
        replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started: fetching every {FETCH_INTERVAL_SECONDS} seconds.")


# ---------- Main ----------
if __name__ == "__main__":
    print("=" * 60)
    print("Flask + Selenium Scheduled Fetcher Dashboard")
    print(f"Target URL: {URL}")
    print(f"Fetch interval: {FETCH_INTERVAL_SECONDS}s")
    print("Dashboard will be available at http://localhost:5000")
    print("=" * 60)

    # Perform an immediate first fetch before starting the web server
    print("Running initial fetch...")
    fetch_json_with_browser()
    print("Initial fetch complete.\n")

    # Start the background scheduler
    start_scheduler()

    # Launch Flask
    app.run(host="0.0.0.0", port=5000, debug=False)
