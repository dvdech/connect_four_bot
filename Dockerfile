FROM python

# working directory for the image
WORKDIR /app

# pip freeze requirements gets [libraries needed for script]
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# copy all files from python directory
COPY . .

RUN apt-get update && apt-get install -y ffmpeg

CMD ["python", "-u", "main.py"]