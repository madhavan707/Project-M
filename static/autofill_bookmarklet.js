/**
 * Instant In-Page Form Auto-Filler
 * Works on ANY browser tab without remote debugging port or setup!
 */
(async function() {
    console.log("[Aadhaar Auto-Filler] Initializing...");

    // Helper notification
    function notify(text, color = '#10b981') {
        let toast = document.getElementById('pan-autofill-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'pan-autofill-toast';
            toast.style = 'position:fixed;top:20px;right:20px;z-index:9999999;padding:12px 20px;border-radius:8px;font-family:sans-serif;font-size:13px;font-weight:600;color:#fff;box-shadow:0 8px 24px rgba(0,0,0,0.4);transition:all 0.3s;pointer-events:none;';
            document.body.appendChild(toast);
        }
        toast.style.background = color;
        toast.innerText = text;
        toast.style.display = 'block';
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => { toast.style.display = 'none'; }, 300);
        }, 4000);
    }

    // 1. Fetch latest record from local app server
    let d = {};
    try {
        const res = await fetch('http://127.0.0.1:8000/api/latest-record');
        d = await res.json();
    } catch(e) {
        notify('⚠️ Could not connect to http://127.0.0.1:8000. Is start.bat running?', '#ef4444');
        return;
    }

    if (!d || (!d.full_name && !d.aadhar_number && !d.pan_number)) {
        notify('⚠️ No document record loaded. Extract an Aadhaar or PAN image first!', '#f59e0b');
        return;
    }

    // Helper functions
    const setText = (selectors, val) => {
        if (!val) return false;
        for (const s of selectors) {
            try {
                const el = typeof s === 'string' ? document.querySelector(s) : s;
                if (el) {
                    el.focus();
                    el.value = String(val).toUpperCase();
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                    return true;
                }
            } catch(e){}
        }
        return false;
    };

    const setSelect = (selectors, matchText) => {
        if (!matchText) return false;
        const search = String(matchText).toUpperCase().trim();
        for (const s of selectors) {
            try {
                const sel = typeof s === 'string' ? document.querySelector(s) : s;
                if (sel && sel.tagName === 'SELECT') {
                    for (let i = 0; i < sel.options.length; i++) {
                        const opt = sel.options[i];
                        if (opt.text.toUpperCase().includes(search) || opt.value.toUpperCase().includes(search)) {
                            sel.selectedIndex = i;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                }
            } catch(e){}
        }
        return false;
    };

    const setRadio = (matchTexts) => {
        const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
        for (const r of radios) {
            const parentText = (r.parentElement ? r.parentElement.innerText : '').toUpperCase();
            const val = (r.value || '').toUpperCase();
            if (matchTexts.some(t => parentText.includes(t.toUpperCase()) || val.includes(t.toUpperCase()))) {
                r.click();
                r.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
        }
        return false;
    };

    const fillGeneric = (key, val) => {
        if (!val || typeof val !== 'string') return false;
        const cleanKey = key.toLowerCase().replace(/[^a-z0-9]/g, '');
        const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
        for (const el of inputs) {
            const name = (el.name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const id = (el.id || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const ph = (el.placeholder || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const label = el.labels && el.labels[0] ? el.labels[0].innerText.toLowerCase().replace(/[^a-z0-9]/g, '') : '';
            if ((name && (name.includes(cleanKey) || cleanKey.includes(name))) ||
                (id && (id.includes(cleanKey) || cleanKey.includes(id))) ||
                (ph && (ph.includes(cleanKey) || cleanKey.includes(ph))) ||
                (label && (label.includes(cleanKey) || cleanKey.includes(label)))) {
                if (el.tagName === 'SELECT') {
                    return setSelect([el], val);
                } else if (el.type !== 'radio' && el.type !== 'checkbox') {
                    return setText([el], val);
                }
            }
        }
        return false;
    };

    // Execution by Section
    window.panAutofillSection = function(section) {
        let count = 0;
        
        // 1. APPLICANT DETAILS
        if (section === 'applicant' || section === 'all') {
            setSelect(['select[name*="category" i]', 'select[id*="category" i]', '#category', '#catApplicant'], 'Individual');
            
            // First, Middle, Last names
            if (setText(['input[name*="first" i]:not([name*="fat" i]):not([name*="mot" i])', 'input[id*="firstname" i]', 'input[placeholder*="First Name" i]'], d.applicant_first_name || d.full_name)) count++;
            if (setText(['input[name*="middle" i]:not([name*="fat" i]):not([name*="mot" i])', 'input[id*="middlename" i]'], d.applicant_middle_name)) count++;
            if (setText(['input[name*="last" i]:not([name*="fat" i]):not([name*="mot" i])', 'input[name*="surname" i]:not([name*="fat" i]):not([name*="mot" i])', 'input[placeholder*="Last Name" i]'], d.applicant_last_name || d.full_name)) count++;
            
            // Name As Per Aadhaar
            if (setText(['input[name*="aspaadhar" i]', 'input[name*="asperaadhaar" i]', 'input[name*="aadhaarname" i]', 'input[name*="aadharname" i]'], d.name_as_per_aadhar || d.full_name)) count++;
            
            // Gender (if radio exists on page)
            if (d.gender) {
                if (setRadio([d.gender])) count++;
                if (setSelect(['select[name*="gender" i]', 'select[id*="gender" i]'], d.gender)) count++;
            }
        }

        // 2. FATHER'S DETAILS & RADIOS
        if (section === 'father' || section === 'all') {
            // Whether single parent: No
            const allRadios = Array.from(document.querySelectorAll('input[type="radio"]'));
            const noRadio = allRadios.find(r => {
                const txt = ((r.parentElement ? r.parentElement.innerText : '') + ' ' + (r.value || '')).toUpperCase();
                return txt.includes('NO') && !txt.includes('NOT');
            });
            if (noRadio) { noRadio.click(); noRadio.dispatchEvent(new Event('change', {bubbles:true})); count++; }

            // Printed on Card: Father
            const fatRadio = allRadios.find(r => {
                const txt = ((r.parentElement ? r.parentElement.innerText : '') + ' ' + (r.value || '')).toUpperCase();
                return txt.includes('FATHER');
            });
            if (fatRadio) { fatRadio.click(); fatRadio.dispatchEvent(new Event('change', {bubbles:true})); count++; }
            
            const fatherFull = d.father_name || [d.father_first_name, d.father_middle_name, d.father_last_name].filter(Boolean).join(' ');
            if (setText(['input[name*="fatfirst" i]', 'input[name*="fatherfirst" i]'], d.father_first_name || fatherFull)) count++;
            if (setText(['input[name*="fatmiddle" i]', 'input[name*="fathermiddle" i]'], d.father_middle_name)) count++;
            if (setText(['input[name*="fatlast" i]', 'input[name*="fatherlast" i]', 'input[name*="fathersurname" i]'], d.father_last_name || fatherFull)) count++;
        }

        // 3. CONTACT & DOB
        if (section === 'contact' || section === 'all') {
            // DOB
            if (setText(['input[name*="dob" i]', 'input[id*="dob" i]', 'input[placeholder*="dd/MM/yyyy" i]', 'input[type="date"]'], d.dob)) count++;
            
            // Residential Status: Resident
            if (setSelect(['select[name*="resident" i]', 'select[id*="resident" i]'], 'Resident')) count++;
            
            // ISD: 91
            if (setSelect(['select[name*="isd" i]', 'select[name*="country" i]'], '91')) count++;
            
            // Mobile
            if (setText(['input[name*="mobile" i]', 'input[id*="mobile" i]', 'input[name*="phone" i]', 'input[placeholder*="Mobile" i]'], d.mobile_number)) count++;
            
            // Email (if available)
            if (d.email || d.email_id) {
                if (setText(['input[name*="email" i]', 'input[id*="email" i]'], d.email || d.email_id)) count++;
            }
        }

        // 4. ADDRESS & STATE
        if (section === 'address' || section === 'all') {
            // Address for Communication: Residence
            if (setSelect(['select[name*="communication" i]', 'select[name*="commaddress" i]'], 'Residence')) count++;
            
            // PAN Card Dispatched / State
            if (setSelect(['select[name*="dispatch" i]', 'select[name*="state" i]'], d.state || 'TAMIL NADU')) count++;
            
            // PIN Code
            if (setText(['input[name*="pin" i]', 'input[id*="pin" i]', 'input[placeholder*="PIN" i]'], d.pincode)) count++;

            // Address Lines (if on this page)
            if (d.address_line_1) setText(['input[name*="flat" i]', 'input[name*="door" i]', 'input[id*="flat" i]', 'input[name*="addr1" i]'], d.address_line_1);
            if (d.address_line_2) setText(['input[name*="premise" i]', 'input[name*="building" i]', 'input[name*="street" i]', 'input[name*="road" i]', 'input[name*="addr2" i]'], d.address_line_2);
        }

        // 5. AADHAAR & PROOFS
        if (section === 'proofs' || section === 'all') {
            const cleanUid = (d.aadhar_number || '').replace(/\s+/g, '');
            if (setText(['input[name*="aadhaar" i]', 'input[name*="uid" i]', 'input[id*="aadhaar" i]'], cleanUid)) count++;
            setSelect(['select[name*="aadhaar" i]'], 'Aadhaar');
            setSelect(['select[name*="identity" i]', 'select[name*="poi" i]'], 'Aadhaar');
            setSelect(['select[name*="address" i]', 'select[name*="poa" i]'], 'Aadhaar');
            setSelect(['select[name*="dobproof" i]', 'select[name*="pod" i]'], 'Aadhaar');
        }

        // 6. ANY OTHER CUSTOM FIELDS
        for (const [k, v] of Object.entries(d)) {
            if (v && typeof v === 'string' && !['isd_code', 'extraction_source'].includes(k)) {
                if (fillGeneric(k, v)) count++;
            }
        }

        notify(`✓ Autofilled ${count} field(s) for "${section}"!`, '#10b981');
    };

    // Auto-execute 'all' immediately on click
    window.panAutofillSection('all');

    // Create Floating HUD if not already present
    if (!document.getElementById('aadhaar-autofill-hud')) {
        const hud = document.createElement('div');
        hud.id = 'aadhaar-autofill-hud';
        hud.style = 'position:fixed;bottom:24px;right:24px;z-index:9999999;background:rgba(15,23,42,0.96);border:1px solid rgba(99,102,241,0.5);border-radius:12px;padding:12px 14px;box-shadow:0 12px 35px rgba(0,0,0,0.6);display:flex;flex-direction:column;gap:8px;font-family:-apple-system,sans-serif;width:230px;backdrop-filter:blur(12px);color:#fff;';

        hud.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:6px;">
            <span style="font-weight:700;font-size:12px;color:#a5b4fc;letter-spacing:0.04em;">⚡ AADHAAR AUTOFILL</span>
            <span style="cursor:pointer;color:#94a3b8;font-size:16px;line-height:1;" onclick="this.parentElement.parentElement.remove()">&times;</span>
          </div>
          <div style="font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            ${d.full_name || 'Card Loaded'}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;">
            <button onclick="panAutofillSection('applicant')" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">1. Name</button>
            <button onclick="panAutofillSection('father')" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">2. Father</button>
            <button onclick="panAutofillSection('contact')" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">3. Contact</button>
            <button onclick="panAutofillSection('address')" style="padding:6px;font-size:11px;font-weight:600;background:#312e81;color:#e0e7ff;border:1px solid #4338ca;border-radius:6px;cursor:pointer;">4. Address</button>
          </div>
          <button onclick="panAutofillSection('all')" style="padding:8px;font-size:12px;font-weight:700;background:linear-gradient(135deg,#6366f1,#06b6d4);color:#fff;border:none;border-radius:6px;cursor:pointer;box-shadow:0 2px 10px rgba(99,102,241,0.3);">⚡ Fill All Fields</button>
        `;
        document.body.appendChild(hud);
    }
})();
