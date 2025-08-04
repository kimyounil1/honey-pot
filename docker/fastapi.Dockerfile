FROM python:3.11-slim

RUN apt update && apt install -y bash && rm -rf /var/lib/apt/lists/*

WORKDIR /src

COPY requirements.txt .
# RUN .venv/bin/pip install --upgrade pip
# RUN .venv/bin/pip install -r requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
CMD ["bash", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
