# app/services/ocr.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import base64
import datetime as dt
import mimetypes
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import json

import fitz  # PyMuPDF
from fastapi import UploadFile
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VISION_MODEL = os.getenv("OCR_VISION_MODEL", "gpt-4o")

async def ocr_file(file: UploadFile) -> str:
    data, mime, filename = await _read_upload(file)
    if _is_pdf(mime, filename, data):
        return _extract_pdf_text_or_vision(data, max_pages=300, dpi=300).strip()
    return _vision_image_to_text(data, mime).strip()

async def extract_diagnosis_fields(file: UploadFile) -> Dict[str, Any]:
    data, mime, filename = await _read_upload(file)
    if _is_pdf(mime, filename, data):
        raw_text = _extract_pdf_text_or_vision(data, max_pages=300, dpi=300)
    else:
        raw_text = _vision_image_to_text(data, mime)
    raw_text = (raw_text or "").strip()

    # 1) 일반 텍스트 파싱
    fields_txt = _parse_fields(raw_text)

    # 2) 비전 직접 추출(이미지일 때 시도)
    fields_vis: Dict[str, Any] = {}
    try:
        if not _is_pdf(mime, filename, data):
            fields_vis = _vision_extract_fields(data, mime)
    except Exception:
        fields_vis = {}

    # 3) 병합: 비전 결과 우선
    # 종합 필드 (주상병 1개 + 보조 다중코드)
    codes_multi: List[str] = []
    if isinstance(fields_vis.get("icd10_codes"), list):
        codes_multi = [str(x) for x in fields_vis.get("icd10_codes") if str(x).strip()]
    # 텍스트에서 보조로 수집(가능하면)
    if not codes_multi and raw_text:
        try:
            packed = raw_text.upper().replace(" ", "")
            found = []
            for m in _ICD_RE.finditer(packed):
                try:
                    found.append(_normalize_icd(m.group(1)))
                except Exception:
                    continue
            # 고유화 순서 유지
            codes_multi = list(dict.fromkeys([c for c in found if c]))
        except Exception:
            pass

    primary_code = (fields_vis.get("icd10_code") or fields_txt.get("icd10_code") or (codes_multi[0] if codes_multi else None))
    fields: Dict[str, Optional[str] | List[str]] = {
        "icd10_code": primary_code,
        "diagnosis_date": (fields_vis.get("diagnosis_date") or fields_txt.get("diagnosis_date")),
        "provider": (fields_vis.get("provider") or fields_txt.get("provider")),
        "disease_name": (fields_vis.get("disease_name") or fields_txt.get("disease_name")),
        "icd10_codes": codes_multi or ([primary_code] if primary_code else []),
    }

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

def _vision_extract_fields(image_bytes: bytes, mime: Optional[str]) -> Dict[str, Optional[str] | List[str]]:
    """진단서 이미지에서 핵심 필드를 직접 추출. 실패 시 빈 dict."""
    if not mime:
        mime = "image/png"
    data_url = _to_data_url(mime, image_bytes)
    system = (
        "너는 한국 의료 진단서를 구조화하는 보조자야. 오직 JSON만 출력해.\n"
        "반드시 다음 키만 포함: icd10_code, icd10_codes, diagnosis_date, provider, disease_name.\n"
        "- icd10_code: 주상병 1개(예: J00, S83.20, U612).\n"
        "- icd10_codes: 문서에서 보이는 모든 ICD/KCD 코드 배열(최대 5개), 없으면 빈 배열.\n"
        "- diagnosis_date: yyyy-mm-dd 또는 null. provider/disease_name도 없으면 null."
    )
    user = [
        {"type": "text", "text": "이미지에서 '질병분류기호(=ICD-10/KCD)', '진단 연월일', '의료기관명', '병명'을 읽어 JSON으로 반환하세요."},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    try:
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
        )
        txt = (resp.choices[0].message.content or "").strip()
        data: Dict[str, Any] = {}
        try:
            data = json.loads(txt)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", txt)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = {}
        codes = []
        if isinstance(data.get("icd10_codes"), list):
            for x in data.get("icd10_codes"):
                try:
                    norm = _normalize_icd(str(x))
                    if norm:
                        codes.append(norm)
                except Exception:
                    pass
        out: Dict[str, Optional[str] | List[str]] = {
            "icd10_code": _normalize_icd(str(data.get("icd10_code") or "")) if data.get("icd10_code") else (codes[0] if codes else None),
            "icd10_codes": codes,
            "diagnosis_date": (str(data.get("diagnosis_date")).strip() or None) if data.get("diagnosis_date") is not None else None,
            "provider": (str(data.get("provider")).strip() or None) if data.get("provider") is not None else None,
            "disease_name": (str(data.get("disease_name")).strip() or None) if data.get("disease_name") is not None else None,
        }
        if (not out.get("icd10_code") or (not out.get("icd10_codes"))) and isinstance(txt, str):
            m2 = _ICD_RE.search(txt.upper().replace(" ", ""))
            if m2:
                pc = _normalize_icd(m2.group(1))
                out["icd10_code"] = out.get("icd10_code") or pc
            # 다중 추출 보강
            try:
                packed = txt.upper().replace(" ", "")
                alls = []
                for m in _ICD_RE.finditer(packed):
                    alls.append(_normalize_icd(m.group(1)))
                if alls:
                    uniq = list(dict.fromkeys([c for c in alls if c]))
                    out["icd10_codes"] = list(dict.fromkeys((out.get("icd10_codes") or []) + uniq))
            except Exception:
                pass
        return out
    except Exception:
        return {}

def _to_data_url(mime: str, data: bytes) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"

# --------------- 필드 파싱 ---------------
# ICD/KCD 코드: 드물게 'U' 계열도 사용되므로 A–Z 전체 허용.
# 세부 코드는 1~3자리까지 방어적으로 허용 (예: S83.20)
_ICD_RE = re.compile(r"\b([A-Z][0-9]{2}(?:[.\-·]?[0-9A-Z]{1,3})?)\b")
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
    # 힌트 키워드 확장 + 공백 제거 후 탐지(예: "상 병 분 류 기 호")
    hints = [
        "ICD", "ICD10", "ICD-10",
        "KCD", "KCD7", "KCD-7",
        "상병코드", "진단코드", "주상병코드",
        "한국표준질병", "질병분류", "질병분류기호", "한국질병분류기호","질병분류번호",
        "상병분류", "상병기호",
    ]
    hints_norm = [h.replace(" ", "").upper() for h in hints]
    for ln in lines:
        ln_norm = re.sub(r"\s+", "", ln).upper()
        if any(h in ln_norm for h in hints_norm):
            m = _ICD_RE.search(ln_norm)
            if m:
                return _normalize_icd(m.group(1))
    blob = re.sub(r"\s+", "", " ".join(lines)).upper()
    m = _ICD_RE.search(blob)
    return _normalize_icd(m.group(1)) if m else None

def _normalize_icd(code: str) -> str:
    c = code.upper().replace("·",".").replace("-",".")
    m = re.match(r"([A-Z])([0-9]{2})(?:\.?([0-9A-Z]{1,3}))?$", c)
    if not m:
        return c
    g1, g2, g3 = m.groups()
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
                # 날짜/행정성 문구는 병명으로 사용하지 않음
                if cand and not _find_date(cand) and not any(x in cand for x in ["연월일", "발행", "진단 연월일", "발급"]):
                    return cand
            if idx + 1 < len(lines):
                cand2 = _clean(lines[idx + 1])
                if cand2 and not _find_date(cand2) and not any(x in cand2 for x in ["연월일", "발행", "진단 연월일", "발급"]):
                    return cand2
    if icd:
        icd_norm = _normalize_icd(icd)
        for i, ln in enumerate(lines):
            if icd_norm in ln.upper().replace(" ", ""):
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    cand = _clean(lines[j])
                    if cand and len(cand) <= 30 and re.search(r"[가-힣]", cand) and not _find_date(cand):
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
