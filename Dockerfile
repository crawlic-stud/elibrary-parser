FROM python:3.10.8

COPY requirements.txt /tmp/requirements.txt
COPY . .

RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["python", "src/main.py"]