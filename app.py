import os
import time
import json
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ================= CONFIGURATION =================
URL = "https://parvezh4x.gamer.gd/cron.php?key=PARVEZH4x412065"

# Setup Bangladesh Timezone (UTC + 6 hours)
BDT = timezone(timedelta(hours=6))
# =================================================

app = Flask(__name__)

# List to store request history logs
bot_logs = []

def add_log(status, details):
    current_time = datetime.now(BDT).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": current_time,
        "status": status,
        "details": details
    }
    bot_logs.insert(0, log_entry) # Insert at the beginning so newest is top
    # Keep only the last 500 logs to save memory
    if len(bot_logs) > 500:
        bot_logs.pop()

def fetch_json_with_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    service = Service("/usr/bin/chromedriver")
    driver = None
    
    start_time = time.time() # Start stopwatch to calculate duration
    
    try:
        current_bdt_time = datetime.now(BDT).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_bdt_time}] Accessing the URL exactly at the start of the minute...")
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        
        driver.get(URL)
        time.sleep(5) # Wait for InfinityFree security bypass
        
        page_source = driver.find_element(By.TAG_NAME, "body").text
        
        end_time = time.time() # Stop stopwatch
        time_taken = round(end_time - start_time, 2) # Calculate duration in seconds
        
        try:
            json_data = json.loads(page_source)
            # Adding execution time (Time Taken) inside the details
            details = f"Executed: {json_data.get('executed', 0)} | JSON Time: {json_data.get('timestamp', 'N/A')} | ⏱️ Time Taken: {time_taken}s"
            add_log("Success", details)
            print(f"✅ Request Success | Time Taken: {time_taken}s")
        except json.JSONDecodeError:
            end_time = time.time()
            time_taken = round(end_time - start_time, 2)
            error_details = page_source[:100] + "..."
            add_log("Failed", f"Invalid JSON. ⏱️ Time Taken: {time_taken}s | Response: {error_details}")
            print(f"❌ Request Failed: Invalid JSON | Time Taken: {time_taken}s")
            
    except Exception as e:
        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        error_msg = str(e)[:100]
        add_log("Error", f"Script Error: {error_msg} | ⏱️ Time Taken: {time_taken}s")
        print(f"❌ Script error occurred | Time Taken: {time_taken}s")
        
    finally:
        if driver is not None:
            try:
                driver.quit() 
            except:
                pass

# Background task for the precise loop
def bot_loop():
    time.sleep(3) # Wait for web server to start
    print("Background bot thread started.")
    print("Waiting for the next exact minute to start...")
    
    while True:
        # Calculate exactly how many seconds are left until the start of the next minute (00 seconds)
        now = datetime.now()
        sleep_seconds = 60 - now.second - (now.microsecond / 1000000.0)
        time.sleep(sleep_seconds)
        
        # When sleep finishes, it is exactly the start of the new minute
        fetch_json_with_browser()

# ================= FRONTEND DASHBOARD =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Status Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #1a1a1a; margin-bottom: 20px; }
        .search-box { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 16px; outline: none; }
        .search-box:focus { border-color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; position: sticky; top: 0; }
        tr:hover { background-color: #f9f9f9; }
        .status-success { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .status-error { color: #fd7e14; font-weight: bold; }
        .no-data { text-align: center; padding: 20px; color: #777; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🤖 Precise Auto Fetch Dashboard (Bangladesh Time)</h2>
        <input type="text" id="searchInput" class="search-box" placeholder="Search by time, status, or details..." onkeyup="filterTable()">
        
        <table id="logsTable">
            <thead>
                <tr>
                    <th>Time (BDT)</th>
                    <th>Status</th>
                    <th>JSON Details & Execution Time</th>
                </tr>
            </thead>
            <tbody id="logsBody">
                <tr><td colspan="3" class="no-data">Waiting for the next exact minute to trigger...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        async function fetchLogs() {
            try {
                const response = await fetch('/api/logs');
                const logs = await response.json();
                const tbody = document.getElementById('logsBody');
                
                if (logs.length === 0) return;
                
                tbody.innerHTML = ''; 
                
                logs.forEach(log => {
                    let statusClass = 'status-error';
                    if(log.status === 'Success') statusClass = 'status-success';
                    if(log.status === 'Failed') statusClass = 'status-failed';
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="white-space: nowrap;">${log.timestamp}</td>
                        <td class="${statusClass}">${log.status}</td>
                        <td>${log.details}</td>
                    `;
                    tbody.appendChild(tr);
                });
                
                filterTable(); 
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        function filterTable() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('logsTable');
            const tr = table.getElementsByTagName('tr');

            for (let i = 1; i < tr.length; i++) { 
                const tds = tr[i].getElementsByTagName('td');
                let match = false;
                for (let j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        if (tds[j].innerHTML.toLowerCase().indexOf(filter) > -1) {
                            match = true;
                            break;
                        }
                    }
                }
                tr[i].style.display = match ? '' : 'none';
            }
        }

        fetchLogs();
        setInterval(fetchLogs, 5000); // UI automatically refreshes every 5 seconds
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/logs')
def get_logs():
    return jsonify(bot_logs)

if __name__ == "__main__":
    # Start the bot thread
    threading.Thread(target=bot_loop, daemon=True).start()
    
    # Start Web Server
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
