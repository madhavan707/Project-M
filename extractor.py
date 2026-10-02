"""
100% Dynamic Aadhaar Extraction Engine (Free & Offline)
- Pure dynamic OCR & QR extraction for ANY Aadhaar card layout
- Auto-rotates if photo is upside down or landscape (0, 90, 180, 270 degrees)
- Multi-lingual relationship, gender, date, and address parsers
- Zero hardcoded names or numbers
- All output normalized to CAPITAL CASE
"""

import re
import cv2
import numpy as np
from PIL import Image
import zlib
import xml.etree.ElementTree as ET
from rapidocr_onnxruntime import RapidOCR

_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = RapidOCR()
        # High-performance tuning: Cap max side length to avoid 25s+ sluggish runs on 12MP phone photos
        try:
            if hasattr(_ocr_engine, 'text_detector') and hasattr(_ocr_engine.text_detector, 'preprocess_op'):
                _ocr_engine.text_detector.preprocess_op[0].limit_type = 'max'
                _ocr_engine.text_detector.preprocess_op[0].limit_side_len = 1280
        except Exception:
            pass
    return _ocr_engine


def clean_caps(text: str) -> str:
    """Helper to clean whitespace, special characters, and normalize to CAPITAL CASE."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip(" ,.-").upper()


def try_decode_qr(image_path: str):
    """
    Dynamically decodes UIDAI Aadhaar QR code if present.
    UIDAI encodes XML or byte-compressed demographic data.
    """
    try:
        import zxingcpp
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Test original, grayscale, and adaptive threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants = [
            img,
            gray,
            cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        ]
        
        for v in variants:
            barcodes = zxingcpp.read_barcodes(v)
            for b in barcodes:
                raw_text = b.text or ""
                # XML format in v1 QR code
                if "<PrintLetterBarcodeData" in raw_text:
                    try:
                        root = ET.fromstring(raw_text)
                        uid = root.attrib.get("uid", "")
                        if len(uid) == 12:
                            uid = f"{uid[:4]} {uid[4:8]} {uid[8:]}"
                        
                        name = root.attrib.get("name", "")
                        co = root.attrib.get("co", "")
                        father = re.sub(r'^(?:S/O|D/O|W/O|C/O|CARE\s*OF)[:\s.-]+', '', co, flags=re.IGNORECASE)
                        dob = root.attrib.get("dob", "")
                        gender = root.attrib.get("gender", "")
                        if gender in ["M", "MALE", "m"]:
                            gender = "MALE"
                        elif gender in ["F", "FEMALE", "f"]:
                            gender = "FEMALE"
                            
                        house = root.attrib.get("house", "")
                        street = root.attrib.get("street", "")
                        lm = root.attrib.get("lm", "")
                        loc = root.attrib.get("loc", "")
                        vtc = root.attrib.get("vtc", "")
                        po = root.attrib.get("po", "")
                        dist = root.attrib.get("dist", "")
                        state = root.attrib.get("state", "")
                        pincode = root.attrib.get("pc", "")
                        
                        addr_1_parts = [p for p in [house, street, lm] if p]
                        addr_2_parts = [p for p in [loc, vtc, po, dist, state] if p]
                        
                        return {
                            "aadhar_number": clean_caps(uid),
                            "full_name": clean_caps(name),
                            "father_name": clean_caps(father),
                            "dob": clean_caps(dob),
                            "gender": clean_caps(gender),
                            "mobile_number": "",
                            "address_line_1": clean_caps(", ".join(addr_1_parts)),
                            "address_line_2": clean_caps(", ".join(addr_2_parts)),
                            "pincode": clean_caps(pincode),
                            "extraction_source": "QR_CODE"
                        }
                    except Exception:
                        pass
    except Exception:
        pass
    return None


def parse_aadhaar_ocr(lines: list) -> dict:
    """
    Completely dynamic parser for ANY Aadhaar card layout, language, or format.
    Zero hardcoded values.
    """
    raw_lines = [l.strip() for l in lines if l and len(l.strip()) > 1]
    
    # 1. Aadhaar Number (12 digits, often with spaces or 4-4-4)
    aadhar_number = ""
    for l in raw_lines:
        # Match 12 digits or 4-4-4 pattern
        m = re.search(r'\b([2-9]\d{3}\s?\d{4}\s?\d{4})\b', l)
        if m:
            clean_digits = re.sub(r'\D', '', m.group(1))
            if len(clean_digits) == 12:
                aadhar_number = f"{clean_digits[:4]} {clean_digits[4:8]} {clean_digits[8:]}"
                break
    
    # 2. Date of Birth (DD/MM/YYYY, DD-MM-YYYY, or Year of Birth)
    dob = ""
    for l in raw_lines:
        m = re.search(r'\b([0-3]?\d[/.-][0-1]?\d[/.-]\d{4})\b', l)
        if m:
            clean_dob = m.group(1).replace('-', '/').replace('.', '/')
            parts = clean_dob.split('/')
            if len(parts) == 3:
                dob = f"{int(parts[0]):02d}/{int(parts[1]):02d}/{parts[2]}"
            break
        # Year of birth only
        m_yob = re.search(r'(?:Year\s*of\s*Birth|YOB|DOB|Birth)[:\s]*(\d{4})', l, re.IGNORECASE)
        if m_yob:
            dob = f"01/01/{m_yob.group(1)}"
            break
            
    # 3. Mobile Number (10 digits starting with 6, 7, 8, 9)
    mobile = ""
    for l in raw_lines:
        m = re.search(r'(?:Mobile|Mob|Phone|Contact)[:\s]*([6-9]\d{9})\b', l, re.IGNORECASE)
        if m:
            mobile = m.group(1)
            break
        # Standalone 10 digit number that is not part of a 12-digit UID
        m_standalone = re.search(r'\b([6-9]\d{9})\b', l)
        if m_standalone and not re.search(r'\d{12}', l):
            mobile = m_standalone.group(1)

    # 4. PIN Code (6 digits, first digit 1-9)
    pincode = ""
    for l in raw_lines:
        m = re.search(r'(?:PIN\s*Code|PIN|Postal)[:\s]*([1-9]\d{5})\b', l, re.IGNORECASE)
        if m:
            pincode = m.group(1)
            break
    if not pincode:
        for l in raw_lines:
            m = re.search(r'\b([1-9]\d{5})\b', l)
            if m:
                pincode = m.group(1)
                break

    # 5. Care of / Father / Guardian Name & Relationship
    father_name = ""
    relation_prefix = ""
    care_of_index = -1
    for idx, l in enumerate(raw_lines):
        # Match S/O, D/O, W/O, C/O, H/O, Father, Husband, Guardian in English, Tamil, Hindi
        m = re.search(r'\b(S/O|D/O|W/O|C/O|H/O|FATHER|HUSBAND|GUARDIAN|தந்தை|पिता)[:\s.-]+([^,:\n]+)', l, re.IGNORECASE)
        if m:
            relation_prefix = m.group(1).upper()
            raw_father = m.group(2).strip()
            raw_father = re.sub(r'[^A-Za-z\s.]', '', raw_father).strip()
            if len(raw_father) >= 2:
                father_name = raw_father
                care_of_index = idx
                break

    # 6. Gender Detection (Multi-language & relationship inference)
    gender = ""
    for l in raw_lines:
        if re.search(r'\b(FEMALE|பெண்|महिला|WOMAN)\b', l, re.IGNORECASE):
            gender = "FEMALE"
            break
        elif re.search(r'\b(MALE|ஆண்|पुरुष|MAN)\b', l, re.IGNORECASE):
            gender = "MALE"
            break
        elif re.search(r'\b(TRANSGENDER|மூன்றாம்\s*பாலினம்)\b', l, re.IGNORECASE):
            gender = "TRANSGENDER"
            break
            
    # If not explicitly printed, infer from relationship marker
    if not gender and relation_prefix:
        if relation_prefix == "S/O":
            gender = "MALE"
        elif relation_prefix in ["D/O", "W/O"]:
            gender = "FEMALE"

    # 7. Full Name Extraction (Dynamic layout analysis)
    full_name = ""
    # Header keywords to ignore
    ignore_words = [
        "government", "govt", "india", "unique", "identification", "authority",
        "uidai", "enrolment", "enrol", "help", "download", "issue", "signature",
        "valid", "aadhaar", "father", "male", "female", "dob", "birth", "to"
    ]
    
    # Method A: Look above the Care of (S/O, C/O) line
    if care_of_index > 0:
        cand = raw_lines[care_of_index - 1]
        if cand.strip().lower() == "to" and care_of_index > 1:
            cand = raw_lines[care_of_index - 2]
        clean_cand = re.sub(r'[^A-Za-z\s.]', '', cand).strip()
        if len(clean_cand) >= 2 and not any(w in clean_cand.lower() for w in ignore_words):
            full_name = clean_cand

    # Method B: Look above DOB on the card face
    if not full_name:
        for idx, l in enumerate(raw_lines):
            if re.search(r'(?:DOB|Birth|YOB|பிறந்த)', l, re.IGNORECASE) and idx > 0:
                cand = raw_lines[idx - 1]
                clean_cand = re.sub(r'[^A-Za-z\s.]', '', cand).strip()
                if len(clean_cand) >= 2 and not any(w in clean_cand.lower() for w in ignore_words):
                    full_name = clean_cand
                    break

    # Method C: Look below "To" block
    if not full_name:
        for idx, l in enumerate(raw_lines):
            if l.strip().lower() == "to" and idx + 1 < len(raw_lines):
                cand = raw_lines[idx + 1]
                clean_cand = re.sub(r'[^A-Za-z\s.]', '', cand).strip()
                if len(clean_cand) >= 2 and not any(w in clean_cand.lower() for w in ignore_words):
                    full_name = clean_cand
                    break

    # 8. Address Extraction (Segmenting into Line 1 and Line 2)
    address_line_1 = ""
    address_line_2 = ""
    
    addr_candidates = []
    start_collecting = False
    for idx, l in enumerate(raw_lines):
        if idx == care_of_index:
            start_collecting = True
            continue
        if start_collecting:
            # Stop if hitting bottom card, mobile, PIN, signature or UID
            if re.search(r'(?:PIN\s*Code|Mobile|Your\s*Aadhaar|Signature|Govemment|Government)', l, re.IGNORECASE):
                break
            if re.search(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b', l):
                break
            cleaned_l = l.strip(" ,.-")
            if cleaned_l and not re.search(r'(?:VID:|Enrolment)', cleaned_l, re.IGNORECASE):
                addr_candidates.append(cleaned_l)

    if addr_candidates:
        line_1_parts = []
        line_2_parts = []
        area_keywords = ["vtc", "po", "post", "sub district", "district", "dist", "state", "taluk", "nagar", "village"]
        
        for cand in addr_candidates:
            cand_lower = cand.lower()
            if any(k in cand_lower for k in area_keywords):
                line_2_parts.append(cand)
            else:
                if len(line_1_parts) < 2:
                    line_1_parts.append(cand)
                else:
                    line_2_parts.append(cand)
                    
        address_line_1 = ", ".join(line_1_parts)
        address_line_2 = ", ".join(line_2_parts)
    else:
        # Fallback if no care of marker: collect address-like lines
        addr_lines = [l for l in raw_lines if any(k in l.lower() for k in ["street", "road", "nagar", "vtc", "district", "state", "colony", "lane", "house", "flat"])]
        if addr_lines:
            address_line_1 = addr_lines[0]
    # Detect State from address
    state = ""
    full_address_text = f"{address_line_1} {address_line_2} {' '.join(raw_lines)}".upper()
    for s in INDIAN_STATES:
        if re.search(r'\b' + re.escape(s) + r'\b', full_address_text):
            state = s
            break

    return {
        "aadhar_number": clean_caps(aadhar_number),
        "full_name": clean_caps(full_name),
        "father_name": clean_caps(father_name),
        "dob": clean_caps(dob),
        "gender": clean_caps(gender),
        "mobile_number": clean_caps(mobile),
        "address_line_1": clean_caps(address_line_1),
        "address_line_2": clean_caps(address_line_2),
        "pincode": clean_caps(pincode),
        "state": clean_caps(state),
        "extraction_source": "DYNAMIC_OCR"
    }


INDIAN_STATES = [
    "ANDAMAN AND NICOBAR ISLANDS", "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR",
    "CHANDIGARH", "CHHATTISGARH", "DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "DELHI",
    "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JAMMU AND KASHMIR", "JHARKHAND",
    "KARNATAKA", "KERALA", "LADAKH", "LAKSHADWEEP", "MADHYA PRADESH", "MAHARASHTRA",
    "MANIPUR", "MEGHALAYA", "MIZORAM", "NAGALAND", "ODISHA", "PUDUCHERRY", "PUNJAB",
    "RAJASTHAN", "SIKKIM", "TAMIL NADU", "TELANGANA", "TRIPURA", "UTTAR PRADESH",
    "UTTARAKHAND", "WEST BENGAL"
]


def expand_initials_from_father(applicant_name: str, father_name: str) -> str:
    """
    South Indian / Tamil Initial Expansion for Indian PAN compliance.
    Single-letter initials are REJECTED in PAN forms.
    If an initial matches the starting letter of any word in Father's name, expand it!
    If no match, leave it alone.
    Handles separated initials ('V KAILASH'), dotted ('V. KAILASH'), and conjoined ('VKAILASH').
    """
    cleaned_name = re.sub(r'[\.\-_/]+', ' ', applicant_name).strip()
    app_words = [w.strip() for w in re.split(r'\s+', cleaned_name) if w.strip()]
    father_words = [w.strip(" .") for w in re.split(r'\s+', father_name.strip()) if len(w.strip(" .")) > 1]

    if not app_words:
        return applicant_name.upper()

    expanded_words = []
    for word in app_words:
        # Case A: Explicit single letter initial, e.g. 'V'
        if len(word) == 1:
            matched_father_word = None
            for fw in father_words:
                if fw.upper().startswith(word.upper()):
                    matched_father_word = fw.upper()
                    break
            if matched_father_word:
                expanded_words.append(matched_father_word)
            else:
                expanded_words.append(word.upper())
        # Case B: Conjoined initial, e.g. 'VKAILASH' where 'V' matches 'VIJAYAN' and 'KAILASH' is a name
        elif len(word) >= 4:
            init = word[0].upper()
            rest = word[1:].upper()
            matched_father_word = None
            for fw in father_words:
                if fw.upper().startswith(init) and fw.upper() != word.upper():
                    matched_father_word = fw.upper()
                    break
            if matched_father_word:
                expanded_words.append(matched_father_word)
                expanded_words.append(rest)
            else:
                expanded_words.append(word.upper())
        else:
            expanded_words.append(word.upper())

    return " ".join(expanded_words)



def split_name_parts(name: str):
    """
    Splits a full name into (First Name, Middle Name, Last Name / Surname).
    In PAN forms: Last Name / Surname is strictly MANDATORY!
    If 1 word: Last Name = word, First = '', Middle = ''
    If 2 words: First = word1, Last = word2
    If 3+ words: First = word1, Middle = middle words, Last = last word
    """
    words = [w.strip(" .") for w in re.split(r'\s+', name.strip()) if w.strip(" .")]
    if not words:
        return "", "", ""
    if len(words) == 1:
        return "", "", words[0].upper()
    elif len(words) == 2:
        return words[0].upper(), "", words[1].upper()
    else:
        return words[0].upper(), " ".join(words[1:-1]).upper(), words[-1].upper()


def enrich_with_pan_fields(data: dict) -> dict:
    """
    Enriches extracted demographic data with decomposed, PAN-compliant fields.
    Guarantees no single-letter First Name if father expansion matches.
    All outputs strictly in CAPITAL CASE.
    """
    raw_name = data.get("full_name", "").strip()
    raw_father = data.get("father_name", "").strip()

    # 1. Expand single-letter initials if matching father's name
    expanded_applicant_name = expand_initials_from_father(raw_name, raw_father)

    # 2. Split applicant name into First, Middle, Last
    app_first, app_mid, app_last = split_name_parts(expanded_applicant_name)

    # 3. Split father's name into First, Middle, Last
    fat_first, fat_mid, fat_last = split_name_parts(raw_father)

    # 4. State resolution
    state = data.get("state", "").strip()
    if not state:
        combined = f"{data.get('address_line_1', '')} {data.get('address_line_2', '')}".upper()
        for s in INDIAN_STATES:
            if s in combined:
                state = s
                break

    data.update({
        "full_name": clean_caps(raw_name),
        "name_as_per_aadhar": clean_caps(raw_name),
        "expanded_name": clean_caps(expanded_applicant_name),
        "applicant_first_name": clean_caps(app_first),
        "applicant_middle_name": clean_caps(app_mid),
        "applicant_last_name": clean_caps(app_last),
        "father_name": clean_caps(raw_father),
        "father_first_name": clean_caps(fat_first),
        "father_middle_name": clean_caps(fat_mid),
        "father_last_name": clean_caps(fat_last),
        "state": clean_caps(state),
        "isd_code": "91",
        "residential_status": "RESIDENT INDIVIDUAL",
        "single_parent": "NO",
        "card_name_printed": "FATHER",
        "address_for_communication": "RESIDENCE",
        "proof_identity": "AADHAAR CARD",
        "proof_address": "AADHAAR CARD",
        "proof_dob": "AADHAAR CARD"
    })
    return data


def rotate_image(image, angle):
    """Rotate image by 90, 180, or 270 degrees."""
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def extract_aadhaar_data(image_path: str) -> dict:
    """
    Main extraction function for ANY dynamic image:
    1. Tests QR code decode.
    2. Runs RapidOCR. If orientation is sideways or upside-down, attempts auto-rotation.
    3. Guarantees 100% CAPITAL CASE output with decomposed PAN fields.
    """
    # 1. Try QR Code
    qr_data = try_decode_qr(image_path)
    if qr_data and qr_data.get("aadhar_number") and qr_data.get("full_name"):
        return enrich_with_pan_fields(qr_data)

    # Pre-scale image if it is too massive (> 1600px)
    img = cv2.imread(image_path)
    if img is not None:
        h, w = img.shape[:2]
        if max(h, w) > 1600:
            scale = 1600.0 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 2. OCR Extraction
    ocr = get_ocr_engine()
    results, _ = ocr(img if img is not None else image_path)
    lines = [item[1] for item in (results or [])]
    extracted = parse_aadhaar_ocr(lines)

    # 3. If neither Aadhaar nor DOB was found, attempt 90/180/270 degree rotation
    if not extracted.get("aadhar_number") and not extracted.get("dob"):
        if img is not None:
            for angle in [90, 180, 270]:
                rot_img = rotate_image(img, angle)
                rot_results, _ = ocr(rot_img)
                rot_lines = [item[1] for item in (rot_results or [])]
                rot_extracted = parse_aadhaar_ocr(rot_lines)
                if rot_extracted.get("aadhar_number") or rot_extracted.get("dob"):
                    extracted = rot_extracted
                    break

    # Merge partial QR data if available
    if qr_data:
        for k, v in qr_data.items():
            if v and not extracted.get(k):
                extracted[k] = v

    return enrich_with_pan_fields(extracted)

