# app/services/ocr.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import base64
import datetime as dt
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from fastapi import UploadFile
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VISION_MODEL = os.getenv("OCR_VISION_MODEL", "gpt-4o-mini")

async def ocr_file(file: UploadFile) -> str:
    data, mime, filename = await _read_upload(file)
    if _is_pdf(mime, filename, data):
        return _extract_pdf_text_or_vision(data, max_pages=5, dpi=300).strip()
    return _vision_image_to_text(data, mime).strip()

async def extract_diagnosis_fields(file: UploadFile) -> Dict[str, Any]:
    data, mime, filename = await _read_upload(file)
    if _is_pdf(mime, filename, data):
        raw_text = _extract_pdf_text_or_vision(data, max_pages=5, dpi=300)
    else:
        raw_text = _vision_image_to_text(data, mime)
    raw_text = (raw_text or "").strip()

    fields = _parse_fields(raw_text)
    conf = _estimate_confidence(fields, raw_text)
    fields["confidence"] = conf
    fields["raw_text"] = raw_text
    return fields

async def _read_upload(file: UploadFile) -> Tuple[bytes, str, str]:
    data = await file.read()
    try:
        await file.seek(0)
    except Exception:
        try:
            file.file.seek(0)  # type: ignore
        except Exception:
            pass
    mime, _ = mimetypes.guess_type(file.filename)
    if mime is None:
        mime = "application/octet-stream"
    return data, mime, file.filename or ""

def _is_pdf(mime: str, filename: str, data: bytes) -> bool:
    if mime == "application/pdf": return True
    if (filename or "").lower().endswith(".pdf"): return True
    return data[:5] == b"%PDF-"

def _extract_pdf_text_or_vision(pdf_bytes: bytes, max_pages: int = 5, dpi: int = 300) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_texts: List[str] = []
    for i in range(min(len(doc), max_pages)):
        t = doc[i].get_text("text") or ""
        page_texts.append(t.strip())
    layer_text = "\n\n".join([t for t in page_texts if t])
    if _is_text_sufficient(page_texts):
        return layer_text
    ocr_texts: List[str] = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        ocr_texts.append(_vision_image_to_text(img_bytes, "image/png"))
    return "\n\n".join([t for t in (layer_text, *ocr_texts) if t])

def _is_text_sufficient(page_texts: List[str]) -> bool:
    if not page_texts: return False
    long_pages = sum(1 for t in page_texts if len(t) > 200)
    return long_pages >= max(1, len(page_texts)//2)

def _vision_image_to_text(image_bytes: bytes, mime: Optional[str]) -> str:
    if not mime: mime = "image/png"
    data_url = _to_data_url(mime, image_bytes)
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role":"user",
            "content":[
                {"type":"text","text":"Extract ONLY the plain text from this image."},
                {"type":"image_url","image_url":{"url":data_url}}
            ]
        }]
    )
    return (resp.choices[0].message.content or "").strip()

def _to_data_url(mime: str, data: bytes) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"

# --------------- 필드 파싱 ---------------
_ICD_RE = re.compile(r"\b([A-TV-Z][0-9]{2}(?:[.\-·]?[0-9A-Z]{1,2})?)\b")
_DATE_RE = [
    re.compile(r"\b(20\d{2}|19\d{2})[./\-년\s]*(1[0-2]|0?[1-9])[./\-월\s]*(3[01]|[12]?\d)[일]?\b"),
    re.compile(r"\b(1[0-2]|0?[1-9])[./\-](3[01]|[12]?\d)[./\-](20\d{2}|19\d{2})\b"),
]
_PROVIDER_HINTS = ["의료기관명","병원","의원","클리닉","센터","병원명","의료재단","보건소"]
_DISEASE_HINTS  = ["상병명","진단명","질병명","병명","상병"]

def _parse_fields(text: str) -> Dict[str, Optional[str]]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    icd  = _extract_icd(lines)
    date = _extract_date(lines)
    prov = _extract_provider(lines)
    dis  = _extract_disease(lines, icd)
    return {
        "icd10_code": icd,
        "diagnosis_date": date,
        "provider": prov,
        "disease_name": dis,
    }

def _extract_icd(lines: List[str]) -> Optional[str]:
    for ln in lines:
        if any(k in ln for k in ["ICD","상병코드","진단코드","상병분류기호","질병코드"]):
            m = _ICD_RE.search(ln.replace(" ","").upper())
            if m: return _normalize_icd(m.group(1))
    blob = " ".join(lines).replace(" ","").upper()
    m = _ICD_RE.search(blob)
    return _normalize_icd(m.group(1)) if m else None

def _normalize_icd(code: str) -> str:
    c = code.upper().replace("·",".").replace("-",".")
    m = re.match(r"([A-TV-Z])([0-9]{2})(?:\.?([0-9A-Z]{1,2}))?$", c)
    if not m: return c
    g1,g2,g3 = m.groups()
    return f"{g1}{g2}" + (f".{g3}" if g3 else "")

def _extract_date(lines: List[str]) -> Optional[str]:
    for ln in lines:
        if any(k in ln for k in ["진단일","진단일자","발병일","진단확정일","진료일자","발급일"]):
            iso = _find_date(ln)
            if iso: return iso
    cands = []
    for ln in lines:
        iso = _find_date(ln)
        if iso: cands.append(iso)
    return sorted(cands)[-1] if cands else None

def _find_date(s: str) -> Optional[str]:
    for r in _DATE_RE:
        m = r.search(s)
        if not m: continue
        g = m.groups()
        if len(g)==3:
            if len(g[0])==4:
                y,mn,d = int(g[0]),int(g[1]),int(g[2])
            else:
                mn,d,y = int(g[0]),int(g[1]),int(g[2])
            try:
                return dt.date(y,mn,d).isoformat()
            except Exception:
                continue
    return None

def _extract_provider(lines: List[str]) -> Optional[str]:
    for ln in lines:
        if any(h in ln for h in _PROVIDER_HINTS):
            parts = re.split(r"[:：\s]{1,}", ln)
            cand = (parts[-1] if parts else "").strip()
            if any(k in cand for k in ["병원","의원","센터","클리닉"]) and len(cand)<=40:
                return cand
    for ln in lines:
        m = re.search(r"([가-힣A-Za-z0-9\s]+(병원|의원|센터|클리닉))", ln)
        if m: return m.group(1).strip()
    return None

def _extract_disease(lines: List[str], icd: Optional[str]) -> Optional[str]:
    for idx, ln in enumerate(lines):
        if any(k in ln for k in _DISEASE_HINTS):
            parts = re.split(r"[:：]", ln, maxsplit=1)
            if len(parts) == 2:
                cand = _clean(parts[1])
                if cand:
                    return cand
            if idx + 1 < len(lines):
                cand2 = _clean(lines[idx + 1])
                if cand2:
                    return cand2
    if icd:
        icd_norm = _normalize_icd(icd)
        for i, ln in enumerate(lines):
            if icd_norm in ln.upper().replace(" ", ""):
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    cand = _clean(lines[j])
                    if cand and len(cand) <= 30 and re.search(r"[가-힣]", cand):
                        return cand
    return None

def _clean(s: str) -> str:
    s = re.sub(r"[(){}[\]<>]","", s.strip())
    s = re.sub(r"\s{2,}", " ", s)
    return s if len(s)>=2 else ""

def _estimate_confidence(fields: Dict[str, Optional[str]], raw_text: str) -> float:
    score = 0.3 if len(raw_text)>100 else 0.1
    if fields.get("icd10_code"): score += 0.35
    if fields.get("diagnosis_date"): score += 0.15
    if fields.get("provider"): score += 0.1
    if fields.get("disease_name"): score += 0.1
    return float(max(0.0, min(1.0, score)))
