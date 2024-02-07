FROM python:3.9
RUN apt-get update && apt-get install -y nginx rabbitmq-server
ENV FLASK_APP=app.py
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80 5672
CMD service nginx start && service rabbitmq-server start && gunicorn -w 4 -b 0.0.0.0:5000 app:app
