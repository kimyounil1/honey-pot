# Base Image: Miniconda3 for a clean Conda environment
FROM continuumio/miniconda3:latest

# Set working directory
WORKDIR /app

# Create a Conda environment with Python 3.9
RUN conda create -n ocr_env python=3.9 -y

# Set the shell to run subsequent commands within the Conda environment
SHELL ["conda", "run", "-n", "ocr_env", "/bin/bash", "-c"]

# Install essential system libraries for image processing and PDF handling
RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx libglib2.0-0 poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Install PaddlePaddle CPU version using Conda for better compatibility
RUN conda install -c paddle paddlepaddle==2.6.0 -y

# Install a compatible version of NumPy to avoid ABI conflicts, then install other libraries via pip.
RUN pip install numpy==1.26.4 paddleocr==2.7 fastapi==0.110.0 uvicorn==0.29.0 python-multipart Pillow pdf2image         

# Copy only the paddleocr application code into the container
COPY app/main.py .

# Expose the port the API will run on
EXPOSE 5000

# Command to run the FastAPI server
CMD uvicorn main:app --host 0.0.0.0 --port 5000
