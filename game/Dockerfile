FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY main.py .

#It is the command that will start and run the FastAPI application container
CMD ["python", "main.py"]
