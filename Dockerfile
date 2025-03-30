FROM python:3.10

RUN apt update && apt install -y \
    weasyprint \
    libpango-1.0-0 \
    libgobject-2.0-0 \
    libcairo2

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "app.py"]
