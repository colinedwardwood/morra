FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY python_player.py .

#It will expose the FastAPI application on port `8000` inside the container
EXPOSE 80

#It is the command that will start and run the FastAPI application container
CMD ["uvicorn", "python_player:app", "--host", "0.0.0.0", "--port", "80"]