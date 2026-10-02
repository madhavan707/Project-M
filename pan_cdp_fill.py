"""
Chrome DevTools Protocol (CDP) PAN Form Auto-Filler
Connects to an open Chrome instance on port 9222 and fills fields step-by-step.
"""

import sys
import json
import asyncio
import urllib.request
import argparse
import websockets

CDP_HTTP = "http://127.0.0.1:9222"
API_URL = "http://127.0.0.1:8000/api/latest-record"


def get_latest_record():
    try:
        req = urllib.request.Request(API_URL)
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"[CDP] Warning: Could not fetch from {API_URL}: {e}")
        return {}


def get_active_tab():
    try:
        req = urllib.request.Request(f"{CDP_HTTP}/json")
        with urllib.request.urlopen(req, timeout=5) as res:
            tabs = json.loads(res.read().decode('utf-8'))
            pages = [t for t in tabs if t.get('type') == 'page']
            if not pages:
                return None
            # Return first page or one that matches portal keywords
            for p in pages:
                url = p.get('url', '').lower()
                title = p.get('title', '').lower()
                if any(k in url or k in title for k in ['pan', 'nsdl', 'uti', '49a', 'tin']):
                    return p
            return pages[0]
    except Exception:
        return None


def check_cdp_status():
    tab = get_active_tab()
    if tab:
        return {
            "connected": True,
            "title": tab.get("title", "Untitled Page"),
            "url": tab.get("url", ""),
            "id": tab.get("id", "")
        }
    return {
        "connected": False,
        "message": "Chrome not reachable on port 9222. Start Chrome using start_chrome_cdp.bat"
    }


async def evaluate_script(ws, js_code: str):
    msg_id = 1
    payload = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True
        }
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    return json.loads(resp)


def build_fill_js(step: str, data: dict) -> str:
    """Builds JavaScript snippet executed in the target page."""
    data_json = json.dumps(data)
    return f"""
    (() => {{
        const d = {data_json};
        const step = "{step}";
        const log = [];

        // Helper to set text value and trigger validation events
        const setText = (selectors, val) => {{
            if (!val) return;
            for (const s of selectors) {{
                const el = document.querySelector(s);
                if (el) {{
                    el.focus();
                    el.value = String(val).toUpperCase();
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    log.push(`Set ${{s}} = ${{val}}`);
                    return true;
                }}
            }}
            return false;
        }};

        // Helper to select dropdown by text or value
        const setSelect = (selectors, matchText) => {{
            if (!matchText) return;
            const search = String(matchText).toUpperCase().trim();
            for (const s of selectors) {{
                const sel = document.querySelector(s);
                if (sel && sel.tagName === 'SELECT') {{
                    for (let i = 0; i < sel.options.length; i++) {{
                        const opt = sel.options[i];
                        if (opt.text.toUpperCase().includes(search) || opt.value.toUpperCase().includes(search)) {{
                            sel.selectedIndex = i;
                            sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            log.push(`Selected ${{s}} = ${{opt.text}}`);
                            return true;
                        }}
                    }}
                }}
            }}
            return false;
        }};

        // Helper to click radio by label or value
        const setRadio = (matchTexts) => {{
            const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
            for (const r of radios) {{
                const parentText = (r.parentElement ? r.parentElement.innerText : '').toUpperCase();
                const val = (r.value || '').toUpperCase();
                if (matchTexts.some(t => parentText.includes(t.toUpperCase()) || val.includes(t.toUpperCase()))) {{
                    r.click();
                    r.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    log.push(`Clicked radio ${{parentText.trim()}}`);
                    return true;
                }}
            }}
            return false;
        }};

        // 1. APPLICANT DETAILS
        if (step === 'applicant' || step === 'all' || step === 'name') {{
            setSelect(['#cat_applicant', 'select[name="cat_applicant"]', 'select[name*="category" i]'], 'Individual');
            
            // Applicant Name
            setText(['#f_name', 'input[name="f_name"]', 'input[name*="first" i]'], d.applicant_first_name);
            setText(['#m_name', 'input[name="m_name"]', 'input[name*="middle" i]'], d.applicant_middle_name);
            setText(['#l_name', 'input[name="l_name"]', 'input[name*="last" i]'], d.applicant_last_name || d.full_name);
            
            // Name As Per Aadhaar
            setText(['#name_aadhaar', 'input[name="name_aadhaar"]', 'input[name*="aadhaarname" i]'], d.name_as_per_aadhar || d.full_name);
        }}

        // 2. PARENTS DETAILS
        if (step === 'parents' || step === 'all' || step === 'father') {{
            // Single Parent: No
            setRadio(['No', 'N']);
            const nmother = document.getElementById('nmother');
            if (nmother) {{ nmother.checked = true; nmother.click(); nmother.dispatchEvent(new Event('change', {{bubbles:true}})); }}

            // Father Name
            setText(['#faf_name', 'input[name="faf_name"]', 'input[name*="fatfirst" i]'], d.father_first_name);
            setText(['#fam_name', 'input[name="fam_name"]', 'input[name*="fatmiddle" i]'], d.father_middle_name);
            setText(['#fal_name', 'input[name="fal_name"]', 'input[name*="fatlast" i]'], d.father_last_name || d.father_name);
        }}

        // 3. CONTACT & DOB
        if (step === 'contact' || step === 'all' || step === 'dob' || step === 'mobile') {{
            // DOB
            setText(['#dob', 'input[name="dob"]', 'input[placeholder*="dd/MM/yyyy" i]'], d.dob);
            
            // Residential Status: Resident (R)
            setSelect(['#residential_status', 'select[name="residential_status"]'], 'Resident');
            setSelect(['#residential_status', 'select[name="residential_status"]'], 'R');
            
            // ISD Code & Mobile
            setSelect(['#mobile_isd', 'select[name="mobile_isd"]'], '91');
            setText(['#mobile_number', 'input[name="mobile_number"]'], d.mobile_number);

            // Email ID
            if (d.email || d.email_id) {{
                setText(['#email_id', 'input[name="email_id"]'], d.email || d.email_id);
            }}
        }}

        // 4. ADDRESS & STATE
        if (step === 'address' || step === 'all') {{
            // Address for Communication: INDIAN
            setSelect(['#add_comm', 'select[name="add_comm"]'], 'INDIAN');
            
            // State
            setSelect(['#user_state', 'select[name="user_state"]'], d.state || 'TAMIL NADU');
            
            // PIN Code
            setText(['#pincode', 'input[name="pincode"]'], d.pincode);

            // Representative Assessee: NO
            const raNo = document.getElementById('appointRA_no');
            if (raNo) {{ raNo.checked = true; raNo.click(); raNo.dispatchEvent(new Event('change', {{bubbles:true}})); }}

            // Aadhaar Dropdown
            const aadhDrop = document.getElementById('check_aadhaar_eid');
            if (aadhDrop) {{
                setSelect([aadhDrop], 'A');
                if (typeof window.showBox === 'function') window.showBox();
            }}

            // Aadhaar Number
            const cleanUid = (d.aadhar_number || '').replace(/\\D/g, '');
            if (cleanUid) {{
                setTimeout(() => {{
                    setText(['#aadhaarNo', 'input[name="aadhaar_num"]'], cleanUid);
                }}, 150);
            }}

            // Proofs
            setSelect(['#proof_id', 'select[name="proof_id"]'], 'AADHAAR');
            setSelect(['#proof_add', 'select[name="proof_add"]'], 'AADHAAR');
        }}
            
            // PIN Code
            setText(['input[name*="pin" i]', 'input[id*="pin" i]', 'input[placeholder*="PIN" i]'], d.pincode);
        }}

        // 5. AADHAAR & PROOFS
        if (step === 'proofs' || step === 'all' || step === 'aadhaar') {{
            // Select Aadhaar option
            setSelect(['select[name*="aadhaar" i]', 'select[id*="aadhaar" i]'], 'Aadhaar');
            
            // Aadhaar Number (cleaned without spaces)
            const cleanUid = (d.aadhar_number || '').replace(/\\s+/g, '');
            setText(['input[name*="aadhaar" i]', 'input[name*="uid" i]', 'input[id*="aadhaar" i]'], cleanUid);
            
            // POI, POA, POD as Aadhaar
            setSelect(['select[name*="identity" i]', 'select[name*="poi" i]', 'select[id*="poi" i]'], 'Aadhaar');
            setSelect(['select[name*="address" i]', 'select[name*="poa" i]', 'select[id*="poa" i]'], 'Aadhaar');
            setSelect(['select[name*="dobproof" i]', 'select[name*="pod" i]', 'select[id*="pod" i]'], 'Aadhaar');
        }}

        // Helper to fill generic/custom field by matching input names, IDs, placeholders, or labels
        const fillGenericField = (key, val) => {{
            if (!val || typeof val !== 'string') return false;
            const cleanKey = key.toLowerCase().replace(/[^a-z0-9]/g, '');
            const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
            for (const el of inputs) {{
                const name = (el.name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const id = (el.id || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const ph = (el.placeholder || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const label = el.labels && el.labels[0] ? el.labels[0].innerText.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
                if ((name && (name.includes(cleanKey) || cleanKey.includes(name))) ||
                    (id && (id.includes(cleanKey) || cleanKey.includes(id))) ||
                    (ph && (ph.includes(cleanKey) || cleanKey.includes(ph))) ||
                    (label && (label.includes(cleanKey) || cleanKey.includes(label)))) {{
                    if (el.tagName === 'SELECT') {{
                        setSelect([el], val);
                        return true;
                    }} else if (el.type !== 'radio' && el.type !== 'checkbox') {{
                        el.focus();
                        el.value = String(val).toUpperCase();
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        log.push(`Matched ${{key}} -> ${{el.name || el.id || el.placeholder || 'input'}}`);
                        return true;
                    }}
                }}
            }}
            return false;
        }};

        // Single field target (e.g. step="field:full_name" or step="field:mobile_number")
        if (step.startsWith('field:')) {{
            const targetKey = step.substring(6);
            if (d[targetKey]) {{
                fillGenericField(targetKey, d[targetKey]);
            }}
        }}

        // In 'all' or 'custom' mode, also try generic matching for any remaining custom keys
        if (step === 'all' || step === 'custom') {{
            for (const [k, v] of Object.entries(d)) {{
                if (typeof v === 'string' && v.trim()) {{
                    fillGenericField(k, v);
                }}
            }}
        }}

        return {{ success: true, step, logs: log }};
    }})();
    """


async def run_cdp_fill(step: str, custom_data: dict = None):
    tab = get_active_tab()
    if not tab:
        print("[CDP] Error: No active tab found. Please launch Chrome with remote debugging on port 9222.")
        return {"status": "error", "message": "Chrome port 9222 not reachable. Launch Chrome with --remote-debugging-port=9222"}

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        print("[CDP] Error: No webSocketDebuggerUrl available for tab.")
        return {"status": "error", "message": "Missing WebSocket URL for tab"}

    data = custom_data or get_latest_record()
    if not data or not data.get("full_name"):
        print("[CDP] Warning: No active Aadhaar record found on server.")

    js_code = build_fill_js(step, data)

    print(f"[CDP] Connecting to tab: {tab.get('title')} ({tab.get('url')[:60]}...)")
    async with websockets.connect(ws_url, max_size=10_000_000) as ws:
        result = await evaluate_script(ws, js_code)
        val = result.get("result", {}).get("result", {}).get("value", {})
        print(f"[CDP] Result for step '{step}':")
        for line in val.get("logs", []):
            print(f"  ✓ {line}")
        return val


def main():
    parser = argparse.ArgumentParser(description="PAN Form Auto-Filler via CDP")
    parser.add_argument("--step", choices=["applicant", "parents", "contact", "address", "proofs", "all", "name", "father", "gender", "dob", "mobile", "aadhaar"], default="all", help="Section to fill")
    args = parser.parse_args()

    asyncio.run(run_cdp_fill(args.step))


if __name__ == "__main__":
    main()
