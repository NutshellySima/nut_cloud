FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP="nut_cloud"
ENV FLASK_ENV="development"

EXPOSE 5000
CMD [ "flask", "init-db" ]
CMD [ "flask", "run", "--host=0.0.0.0" ]