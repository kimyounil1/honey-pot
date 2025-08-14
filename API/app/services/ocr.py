import base64
import mimetypes
import os

from fastapi import UploadFile
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def ocr_file(file: UploadFile) -> str:
    data = await file.read()
    mime, _ = mimetypes.guess_type(file.filename)
    if mime is None:
        mime = "application/octet-stream"

    if mime == "application/pdf":
        import fitz  # PyMuPDF

        text = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                text.append(page.get_text())
        return "".join(text)

    if mime.startswith("image/"):
        b64 = base64.b64encode(data).decode("utf-8")
        resp = await client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Extract text from this document."},
                        {"type": "input_image", "image": {"base64": b64, "mime_type": mime}},
                    ],
                }
            ],
        )
        return getattr(resp, "output_text", "")

    return ""
