"""
Google Sheets Synchronization & Export Engine (100% Free)
Supports:
1. Google Apps Script Webhook POST (instant sync to user's sheet with zero cloud setup)
2. Local CSV Export (backup & offline usage)
"""

import os
import csv
import json
import requests
from datetime import datetime

CSV_FILE = "aadhaar_extracted_records.csv"

# 17 PAN & Aadhaar Fields in Capitalized Headers (TIMESTAMP removed)
HEADERS = [
    "DOCUMENT TYPE",
    "PAN NUMBER",
    "AADHAAR NUMBER",
    "APPLICANT FIRST NAME",
    "APPLICANT MIDDLE NAME",
    "APPLICANT LAST NAME",
    "NAME AS PER AADHAAR / PAN",
    "FATHER FIRST NAME",
    "FATHER MIDDLE NAME",
    "FATHER LAST NAME",
    "DOB",
    "GENDER",
    "MOBILE NUMBER",
    "ADDRESS LINE 1",
    "ADDRESS LINE 2",
    "PINCODE",
    "STATE"
]

def append_to_local_csv(data: dict) -> str:
    """Appends record to local CSV file with PAN & Aadhaar fields without timestamp."""
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADERS)
        writer.writerow([
            data.get("document_type", "AADHAAR CARD").upper(),
            data.get("pan_number", "").upper(),
            data.get("aadhar_number", "").upper(),
            data.get("applicant_first_name", "").upper(),
            data.get("applicant_middle_name", "").upper(),
            data.get("applicant_last_name", "").upper(),
            (data.get("name_as_per_pan") or data.get("name_as_per_aadhar") or data.get("full_name", "")).upper(),
            data.get("father_first_name", "").upper(),
            data.get("father_middle_name", "").upper(),
            data.get("father_last_name", "").upper(),
            data.get("dob", "").upper(),
            data.get("gender", "").upper(),
            data.get("mobile_number", "").upper(),
            data.get("address_line_1", "").upper(),
            data.get("address_line_2", "").upper(),
            data.get("pincode", "").upper(),
            data.get("state", "").upper()
        ])
    return os.path.abspath(CSV_FILE)


def append_batch_to_local_csv(records: list) -> str:
    """Appends multiple records to local CSV file with PAN & Aadhaar fields without timestamp."""
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADERS)
        for data in records:
            writer.writerow([
                data.get("document_type", "AADHAAR CARD").upper(),
                data.get("pan_number", "").upper(),
                data.get("aadhar_number", "").upper(),
                data.get("applicant_first_name", "").upper(),
                data.get("applicant_middle_name", "").upper(),
                data.get("applicant_last_name", "").upper(),
                (data.get("name_as_per_pan") or data.get("name_as_per_aadhar") or data.get("full_name", "")).upper(),
                data.get("father_first_name", "").upper(),
                data.get("father_middle_name", "").upper(),
                data.get("father_last_name", "").upper(),
                data.get("dob", "").upper(),
                data.get("gender", "").upper(),
                data.get("mobile_number", "").upper(),
                data.get("address_line_1", "").upper(),
                data.get("address_line_2", "").upper(),
                data.get("pincode", "").upper(),
                data.get("state", "").upper()
            ])
    return os.path.abspath(CSV_FILE)


def normalize_record(data: dict) -> dict:
    """Normalizes record fields to clean UPPERCASE without timestamp."""
    full_nm = str(data.get("name_as_per_pan") or data.get("name_as_per_aadhar") or data.get("full_name", "")).upper().strip()
    return {
        "document_type": str(data.get("document_type", "AADHAAR CARD")).upper().strip(),
        "pan_number": str(data.get("pan_number", "")).upper().strip(),
        "aadhar_number": str(data.get("aadhar_number", "")).upper().strip(),
        "applicant_first_name": str(data.get("applicant_first_name", "")).upper().strip(),
        "applicant_middle_name": str(data.get("applicant_middle_name", "")).upper().strip(),
        "applicant_last_name": str(data.get("applicant_last_name", "")).upper().strip(),
        "name_as_per_pan": full_nm,
        "name_as_per_aadhar": full_nm,
        "full_name": full_nm,
        "father_name": str(data.get("father_name", "")).upper().strip(),
        "father_first_name": str(data.get("father_first_name", "")).upper().strip(),
        "father_middle_name": str(data.get("father_middle_name", "")).upper().strip(),
        "father_last_name": str(data.get("father_last_name", "")).upper().strip(),
        "dob": str(data.get("dob", "")).upper().strip(),
        "gender": str(data.get("gender", "")).upper().strip(),
        "mobile_number": str(data.get("mobile_number", "")).upper().strip(),
        "address_line_1": str(data.get("address_line_1", "")).upper().strip(),
        "address_line_2": str(data.get("address_line_2", "")).upper().strip(),
        "pincode": str(data.get("pincode", "")).upper().strip(),
        "state": str(data.get("state", "")).upper().strip()
    }



def push_to_google_sheet(webhook_url: str, data) -> dict:
    """
    Sends single or multiple extracted records to user's Google Sheet via Apps Script Webhook.
    Guarantees all values sent are in CAPITAL CASE and TIMESTAMP is excluded.
    Supports either a single dict or a list of dicts.
    """
    if not webhook_url or not webhook_url.startswith("http"):
        return {"status": "error", "message": "Missing Webhook URL. Please set your Google Apps Script Webhook URL in Sheets Setup."}
        
    if "docs.google.com/spreadsheets" in webhook_url:
        return {
            "status": "error",
            "message": "You pasted the Google Sheet document URL (docs.google.com/spreadsheets/...) instead of the Apps Script Webhook URL! Google requires a Web App URL (script.google.com/macros/s/.../exec). Click 'Sheets Setup' in the header for the setup guide."
        }

    if isinstance(data, list):
        payload = [normalize_record(r) for r in data]
        record_count = len(payload)
    else:
        payload = normalize_record(data)
        record_count = 1
    
    try:
        # Follow redirects since Google Apps Script web apps respond with 302 to script.googleusercontent.com
        res = requests.post(webhook_url, json=payload, timeout=30, allow_redirects=True)
        if res.status_code in [200, 201]:
            count_msg = f"{record_count} record(s)" if record_count > 1 else "Record"
            return {"status": "success", "message": f"{count_msg} successfully added to Google Sheet!"}
        else:
            return {"status": "error", "message": f"Webhook returned HTTP {res.status_code}: {res.text[:150]}"}
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}

