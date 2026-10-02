/**
 * Protean Form 49A 1-Click Native In-Page Auto-Filler
 * Built from EXACT Protean Form 49A DOM elements
 */

(function() {
  console.log("[Aadhaar Autofill Extension] Loaded for Protean Form 49A");

  function showToast(msg, isSuccess = true) {
    let t = document.getElementById("pan-ext-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "pan-ext-toast";
      t.style = "position:fixed;top:18px;left:50%;transform:translateX(-50%);z-index:99999999;padding:12px 24px;border-radius:10px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:14px;font-weight:700;color:#fff;box-shadow:0 12px 35px rgba(0,0,0,0.5);transition:all 0.3s;pointer-events:none;";
      document.body.appendChild(t);
    }
    t.style.background = isSuccess ? "linear-gradient(135deg, #059669, #10b981)" : "linear-gradient(135deg, #dc2626, #ef4444)";
    t.innerText = msg;
    t.style.display = "block";
    t.style.opacity = "1";
    setTimeout(() => {
      t.style.opacity = "0";
      setTimeout(() => { t.style.display = "none"; }, 300);
    }, 4500);
  }

  function highlight(el) {
    if (!el) return;
    try {
      el.style.backgroundColor = "#dcfce7";
      el.style.border = "2px solid #16a34a";
      el.style.transition = "all 0.25s";
    } catch(e) {}
  }

  function setInputValue(id, val) {
    if (val === undefined || val === null || val === "") return false;
    const el = typeof id === "string" ? document.getElementById(id) : id;
    if (!el) return false;
    try {
      el.focus();
      el.value = String(val).toUpperCase().trim();
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      el.dispatchEvent(new Event("blur", { bubbles: true }));
      highlight(el);
      return true;
    } catch(e) {
      return false;
    }
  }

  function setSelectValue(id, valOrText) {
    if (!valOrText) return false;
    const sel = typeof id === "string" ? document.getElementById(id) : id;
    if (!sel) return false;
    try {
      const search = String(valOrText).toUpperCase().trim();
      let matched = false;
      for (let i = 0; i < sel.options.length; i++) {
        const opt = sel.options[i];
        if (opt.value.toUpperCase() === search || opt.text.toUpperCase().includes(search)) {
          sel.selectedIndex = i;
          matched = true;
          break;
        }
      }
      if (matched) {
        sel.dispatchEvent(new Event("change", { bubbles: true }));
        highlight(sel);
        return true;
      }
    } catch(e) {}
    return false;
  }

  function setRadioChecked(id) {
    const r = typeof id === "string" ? document.getElementById(id) : id;
    if (!r) return false;
    try {
      r.checked = true;
      r.click();
      r.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    } catch(e) {
      return false;
    }
  }

  async function performAutofill(section = "all") {
    let d = {};
    try {
      const res = await fetch("http://127.0.0.1:8000/api/latest-record");
      d = await res.json();
    } catch(e) {
      showToast("⚠️ Extractor app not running at http://127.0.0.1:8000", false);
      return;
    }

    if (!d || (!d.full_name && !d.name_as_per_aadhar && !d.aadhar_number)) {
      showToast("⚠️ No Aadhaar record found. Extract a card first!", false);
      return;
    }

    let count = 0;

    // 1. APPLICANT DETAILS
    if (section === "all" || section === "name") {
      // Category: Individual
      if (setSelectValue("cat_applicant", "Individual")) count++;

      // Applicant Names (First, Middle, Last)
      if (setInputValue("f_name", d.applicant_first_name)) count++;
      if (setInputValue("m_name", d.applicant_middle_name)) count++;
      if (setInputValue("l_name", d.applicant_last_name || d.full_name)) count++;
    }

    // 2. FATHER & SINGLE PARENT
    if (section === "all" || section === "father") {
      // Single Parent: No (nmother)
      if (setRadioChecked("nmother")) count++;

      // Father Names (First, Middle, Last)
      const fatherLast = d.father_last_name || d.father_name;
      if (setInputValue("faf_name", d.father_first_name)) count++;
      if (setInputValue("fam_name", d.father_middle_name)) count++;
      if (setInputValue("fal_name", fatherLast)) count++;
    }

    // 3. DOB, RESIDENTIAL STATUS & CONTACT
    if (section === "all" || section === "contact") {
      // DOB (dd/MM/yyyy)
      if (setInputValue("dob", d.dob)) count++;

      // Residential Status: Resident (R)
      if (setSelectValue("residential_status", "R")) count++;

      // ISD: India (91)
      if (setSelectValue("mobile_isd", "91")) count++;

      // Mobile Number
      if (setInputValue("mobile_number", d.mobile_number)) count++;

      // Email ID
      if (d.email || d.email_id) {
        if (setInputValue("email_id", d.email || d.email_id)) count++;
      }
    }

    // 4. ADDRESS, STATE, PIN, AADHAAR & PROOFS
    if (section === "all" || section === "address") {
      // Address for Communication: INDIAN
      if (setSelectValue("add_comm", "INDIAN")) count++;

      // Name As Per Aadhaar
      if (setInputValue("name_aadhaar", d.name_as_per_aadhar || d.full_name)) count++;

      // PAN Card dispatched State (e.g. TAMIL NADU)
      if (setSelectValue("user_state", d.state || "TAMIL NADU")) count++;

      // PIN Code
      if (setInputValue("pincode", d.pincode)) count++;

      // Representative Assessee: NO (appointRA_no)
      if (setRadioChecked("appointRA_no")) count++;

      // Aadhaar Dropdown -> "A" (triggers showBox to reveal aadhaarNo input)
      const aadhaarSel = document.getElementById("check_aadhaar_eid");
      if (aadhaarSel) {
        setSelectValue(aadhaarSel, "A");
        if (typeof window.showBox === "function") window.showBox();
      }

      // Aadhaar Number (12 digits clean)
      const cleanUid = (d.aadhar_number || "").replace(/\D/g, "");
      if (cleanUid) {
        setTimeout(() => {
          setInputValue("aadhaarNo", cleanUid);
        }, 150);
        count++;
      }

      // Proof of Identity: Aadhaar
      if (setSelectValue("proof_id", "AADHAAR")) count++;

      // Proof of Address: Aadhaar
      if (setSelectValue("proof_add", "AADHAAR")) count++;
    }

    showToast(`✓ Successfully filled ${count} fields for ${d.full_name || d.name_as_per_aadhar}!`, true);
  }

  // Create floating widget on page
  function createWidget() {
    if (document.getElementById("pan-autofill-widget")) return;

    const w = document.createElement("div");
    w.id = "pan-autofill-widget";
    w.style = "position:fixed;top:16px;right:16px;z-index:9999999;background:rgba(15,23,42,0.96);border:1px solid #6366f1;border-radius:12px;padding:12px 14px;box-shadow:0 12px 35px rgba(0,0,0,0.6);display:flex;flex-direction:column;gap:8px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;width:240px;backdrop-filter:blur(10px);color:#fff;";

    w.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.12);padding-bottom:6px;">
        <span style="font-weight:700;font-size:12px;color:#a5b4fc;letter-spacing:0.04em;">⚡ AADHAAR AUTOFILL</span>
        <button id="pan-widget-close" style="background:transparent;border:none;color:#94a3b8;font-size:16px;cursor:pointer;line-height:1;">&times;</button>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;">
        <button id="pan-fill-name" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">👤 1. Name</button>
        <button id="pan-fill-father" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">👨 2. Father</button>
        <button id="pan-fill-contact" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">🎂 3. Contact</button>
        <button id="pan-fill-address" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">🏠 4. Address</button>
      </div>
      <button id="pan-fill-all" style="padding:10px;font-size:13px;font-weight:700;background:linear-gradient(135deg,#059669,#10b981);color:#fff;border:none;border-radius:8px;cursor:pointer;box-shadow:0 3px 12px rgba(16,185,129,0.4);display:flex;align-items:center;justify-content:center;gap:6px;">
        ⚡ Fill All Fields
      </button>
    `;

    document.body.appendChild(w);

    document.getElementById("pan-widget-close").onclick = () => w.remove();
    document.getElementById("pan-fill-name").onclick = () => performAutofill("name");
    document.getElementById("pan-fill-father").onclick = () => performAutofill("father");
    document.getElementById("pan-fill-contact").onclick = () => performAutofill("contact");
    document.getElementById("pan-fill-address").onclick = () => performAutofill("address");
    document.getElementById("pan-fill-all").onclick = () => performAutofill("all");
  }

  createWidget();
})();
