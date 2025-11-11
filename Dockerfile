FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# System dependencies for Pillow & fonts, including wget
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    fonts-dejavu-core \
    fonts-noto-cjk \
    fonts-takao \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app

RUN mkdir -p /app/data/backgrounds /app/data/hooks /app/data/composed /app/data/products /app/data/reports
ENV PATH="/app:${PATH}"

#CMD ["python", "main.py", "run-all"]