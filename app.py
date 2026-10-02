"""
FastAPI Server for Aadhaar Extraction & Google Sheets Pipeline
"""

import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from extractor import extract_aadhaar_data, clean_caps
from sheets_sync import push_to_google_sheet, append_to_local_csv, append_batch_to_local_csv, CSV_FILE

app = FastAPI(title="Aadhaar Extractor & Google Sheets Pipeline")

# Enable CORS for downstream extension/userscript autofill
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory storage for the latest record (for instant downstream autofill API)
# In-memory storage for the latest record (for instant downstream autofill API)
latest_record = {
    "aadhar_number": "",
    "full_name": "",
    "name_as_per_aadhar": "",
    "applicant_first_name": "",
    "applicant_middle_name": "",
    "applicant_last_name": "",
    "father_name": "",
    "father_first_name": "",
    "father_middle_name": "",
    "father_last_name": "",
    "dob": "",
    "gender": "",
    "mobile_number": "",
    "address_line_1": "",
    "address_line_2": "",
    "pincode": "",
    "state": "",
    "isd_code": "91",
    "residential_status": "RESIDENT INDIVIDUAL",
    "single_parent": "NO",
    "card_name_printed": "FATHER",
    "address_for_communication": "RESIDENCE",
    "proof_identity": "AADHAAR CARD",
    "proof_address": "AADHAAR CARD",
    "proof_dob": "AADHAAR CARD"
}

class RecordUpdate(BaseModel):
    aadhar_number: str = ""
    full_name: str = ""
    name_as_per_aadhar: str = ""
    applicant_first_name: str = ""
    applicant_middle_name: str = ""
    applicant_last_name: str = ""
    father_name: str = ""
    father_first_name: str = ""
    father_middle_name: str = ""
    father_last_name: str = ""
    dob: str = ""
    gender: str = ""
    mobile_number: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    pincode: str = ""
    state: str = ""
    webhook_url: Optional[str] = None


class BatchSyncRequest(BaseModel):
    records: List[RecordUpdate]
    webhook_url: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Aadhaar Extractor Server is running. UI is loading...</h1>"


@app.post("/api/extract")
async def extract_endpoint(file: UploadFile = File(...)):
    """Uploads Aadhaar image, executes dynamic OCR/QR extraction, and returns capitalized JSON."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        data = extract_aadhaar_data(file_path)
        # Update latest record for autofill queue
        global latest_record
        latest_record = data
        # Save to local CSV backup
        append_to_local_csv(data)
        
        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "data": data
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/sync-sheets")
async def sync_sheets_endpoint(record: RecordUpdate):
    """Pushes verified record to user's Google Sheet via Apps Script Webhook."""
    data_dict = {
        "aadhar_number": clean_caps(record.aadhar_number),
        "applicant_first_name": clean_caps(record.applicant_first_name),
        "applicant_middle_name": clean_caps(record.applicant_middle_name),
        "applicant_last_name": clean_caps(record.applicant_last_name),
        "name_as_per_aadhar": clean_caps(record.name_as_per_aadhar or record.full_name),
        "father_first_name": clean_caps(record.father_first_name),
        "father_middle_name": clean_caps(record.father_middle_name),
        "father_last_name": clean_caps(record.father_last_name),
        "dob": clean_caps(record.dob),
        "gender": clean_caps(record.gender),
        "mobile_number": clean_caps(record.mobile_number),
        "address_line_1": clean_caps(record.address_line_1),
        "address_line_2": clean_caps(record.address_line_2),
        "pincode": clean_caps(record.pincode),
        "state": clean_caps(record.state)
    }
    
    global latest_record
    latest_record = {**latest_record, **data_dict}
    
    # Save local CSV
    append_to_local_csv(data_dict)
    
    if record.webhook_url:
        res = push_to_google_sheet(record.webhook_url, data_dict)
        return JSONResponse(content=res)
    else:
        return JSONResponse(content={
            "status": "warning",
            "message": "Saved locally in CSV, but no Google Apps Script Webhook URL was provided."
        })


@app.post("/api/sync-sheets-batch")
async def sync_sheets_batch_endpoint(batch: BatchSyncRequest):
    """Pushes multiple verified records to user's Google Sheet in one call."""
    if not batch.records:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No records provided in batch."})

    cleaned_list = []
    for r in batch.records:
        cleaned_list.append({
            "aadhar_number": clean_caps(r.aadhar_number),
            "applicant_first_name": clean_caps(r.applicant_first_name),
            "applicant_middle_name": clean_caps(r.applicant_middle_name),
            "applicant_last_name": clean_caps(r.applicant_last_name),
            "name_as_per_aadhar": clean_caps(r.name_as_per_aadhar or r.full_name),
            "father_first_name": clean_caps(r.father_first_name),
            "father_middle_name": clean_caps(r.father_middle_name),
            "father_last_name": clean_caps(r.father_last_name),
            "dob": clean_caps(r.dob),
            "gender": clean_caps(r.gender),
            "mobile_number": clean_caps(r.mobile_number),
            "address_line_1": clean_caps(r.address_line_1),
            "address_line_2": clean_caps(r.address_line_2),
            "pincode": clean_caps(r.pincode),
            "state": clean_caps(r.state)
        })

    # Update latest record to the last one
    if cleaned_list:
        global latest_record
        latest_record = {**latest_record, **cleaned_list[-1]}

    # Save to local CSV
    append_batch_to_local_csv(cleaned_list)

    if batch.webhook_url:
        res = push_to_google_sheet(batch.webhook_url, cleaned_list)
        return JSONResponse(content=res)
    else:
        return JSONResponse(content={
            "status": "warning",
            "message": f"{len(cleaned_list)} records saved locally in CSV, but no Google Apps Script Webhook URL was provided."
        })


@app.get("/api/latest-record")
def get_latest_record():
    """Endpoint for downstream Tampermonkey userscript or Playwright bot to fetch current data."""
    return JSONResponse(content=latest_record)


@app.post("/api/update-record")
async def update_record_endpoint(payload: dict):
    """Allows UI to add, update, edit or delete arbitrary fields dynamically."""
    global latest_record
    fields = payload.get("fields", payload)
    # Update latest_record with sanitized uppercase values
    cleaned = {}
    for k, v in fields.items():
        if v is not None:
            cleaned[str(k).strip()] = str(v).upper().strip()
    latest_record = cleaned
    append_to_local_csv(latest_record)
    return JSONResponse(content={"status": "success", "message": "Record fields updated successfully", "data": latest_record})


@app.get("/api/cdp-status")
def cdp_status_endpoint():
    """Checks whether Chrome is running with remote debugging port 9222 and returns target tab details."""
    from pan_cdp_fill import check_cdp_status
    return JSONResponse(content=check_cdp_status())


@app.post("/api/launch-chrome")
def launch_chrome_endpoint():
    """Launches Google Chrome (or Edge) with remote debugging enabled on port 9222."""
    import subprocess
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    browser_exe = next((p for p in candidates if os.path.exists(p)), None)
    if not browser_exe:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Chrome or Edge could not be found automatically."})
    
    user_data = os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "chrome_automation_profile")
    cmd = [
        browser_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data}"
    ]
    try:
        subprocess.Popen(cmd)
        return JSONResponse(content={"status": "success", "message": f"Browser launched with debugging on port 9222! ({os.path.basename(browser_exe)})"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/cdp-fill")
async def cdp_fill_endpoint(step: str = "all"):
    """Trigger step-by-step or full CDP autofill in Chrome connected on port 9222."""
    from pan_cdp_fill import run_cdp_fill
    res = await run_cdp_fill(step, latest_record)
    return JSONResponse(content=res or {"status": "error", "message": "CDP execution returned empty"})


@app.get("/api/download-csv")
def download_csv():

    """Download the cumulative CSV file of extracted records."""
    csv_path = os.path.abspath(CSV_FILE)
    if os.path.exists(csv_path):
        return FileResponse(csv_path, media_type="text/csv", filename="aadhaar_records.csv")
    raise HTTPException(status_code=404, detail="No records exported yet.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
