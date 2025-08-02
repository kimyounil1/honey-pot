from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
import os
from paddleocr import PaddleOCR
from tempfile import NamedTemporaryFile

app = FastAPI()

# PaddleOCR 초기화 (영어 + 한국어 예시)
ocr = PaddleOCR(use_angle_cls=True, lang='korean')  # 'en', 'korean', 'ch', ...

@app.post("/ocr")
async def ocr_file(file: UploadFile = File(...)):
    # 임시 파일로 저장
    suffix = os.path.splitext(file.filename)[1]
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # OCR 수행
    result = ocr.ocr(tmp_path, cls=True)
    
    # 결과 파싱
    texts = []
    for line in result[0]:
        texts.append(line[1][0])  # 인식된 텍스트

    os.remove(tmp_path)
    return JSONResponse({"filename": file.filename, "texts": texts})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
