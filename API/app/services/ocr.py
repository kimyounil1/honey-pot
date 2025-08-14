import base64
import mimetypes
import os
import fitz  # PyMuPDF
from fastapi import UploadFile
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def ocr_file(file: UploadFile) -> str:
    data = await file.read()
    mime, _ = mimetypes.guess_type(file.filename)
    if mime is None:
        mime = "application/octet-stream"

    # 1) PDF: 텍스트 레이어가 있으면 PyMuPDF로 바로 추출 (비용 0원)
    if mime == "application/pdf":
        text_chunks = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                # 필요시 "text" 대신 "blocks" / "rawdict" 등으로 더 정교하게 추출 가능
                text_chunks.append(page.get_text("text"))
        return "".join(text_chunks).strip()

    # 2) 이미지: GPT-4o-mini Vision으로 OCR
    if mime.startswith("image/"):
        b64 = base64.b64encode(data).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"

        resp = client.chat.completions.create(
            model=os.getenv("ROUTER_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract ONLY the plain text from this image."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        # chat.completions는 choices[0].message.content 로 받습니다.
        return (resp.choices[0].message.content or "").strip()

    return ""
