# Dynamic Aadhaar Extractor & Direct Site Autofill

A **100% free, zero-cost** tool to dynamically extract demographic & address details from **any Aadhaar card layout** and **directly autofill them into any website / portal you have opened or logged into**—without requiring Google Sheets!

All extracted values are automatically normalized to **CAPITAL CASE**.

---

## ⚡ Direct Site Autofill (No Sheets Setup Required!)

Instead of going through Google Sheets webhooks, you can directly use the extracted data to fill whatever site you have open:

1. **Launch Chrome with Remote Debugging**:
   - Double-click [`start_chrome_cdp.bat`](file:///d:/Github/Project%20M/start_chrome_cdp.bat)
   - Open and log in to your target portal (e.g. NSDL, UTIITSL, Government or Banking portal).
2. **One-Click Autofill**:
   - In the web app (`http://127.0.0.1:8000`), click **`🚀 Autofill Browser`** or step buttons:
     - `👤 Name & Gender`
     - `👨 Father`
     - `🎂 DOB & Mobile`
     - `🏠 Address & PIN`
     - `🪪 Aadhaar / Proofs`
   - Or click the **`⚡ Fill`** button next to any specific field to send just that field into the active portal tab!

---

## 🛠️ Dynamic Field Manager (Add, Remove, Edit & Update)

You have full control over the fields for every card:

- **➕ Add Field**: Add any custom field on the fly (`Email`, `PAN Number`, `Voter ID`, `Ration Card`, `Spouse Name`, `District`, etc.).
- **✕ Remove Field**: Delete any field with a single click if not needed.
- **✎ Edit / Update**: Click any field name to rename it, or type directly into any value box to edit it in real-time.
- **🏷️ View Presets**:
  - **🪪 Standard (Individual)** *(Default)*: Clean view with Full Name, Aadhaar Number, DOB, Gender, Mobile, Father's Name, Address, PIN, and State. No unwanted PAN-specific subfields!
  - **📝 PAN 49A (Decomposed)**: When needed, displays separated First, Middle, Last names with father name expansion.
  - **📋 All Fields**: Shows all extracted and custom keys.

---

## 🚀 How to Run the Tool

1. Double-click [`start.bat`](file:///d:/Github/Project%20M/start.bat) or run:
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Open your browser to: **`http://127.0.0.1:8000`**
3. Upload an Aadhaar image (JPEG, PNG, PDF cutout) or drag-and-drop multiple cards.
4. Review, edit, add, or remove fields, then click **`🚀 Autofill Browser`**!

---

## 📁 Offline & Optional Exports

- **Download CSV**: Instant offline spreadsheet download with 1 click.
- **Copy JSON / Copy Text**: Clean formatted text or JSON to clipboard.
- **Google Sheets Sync (Optional)**: If you ever want cloud sync, click `Google Sheet (Optional)` in the bottom bar to connect an Apps Script Webhook.
