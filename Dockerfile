FROM python:3.10

WORKDIR /opt/twitch-auto-recorder-3000

RUN apt-get update
RUN apt-get install -y ffmpeg build-essential

RUN pip install "setuptools==57.5.0"

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY requirements-plugins.txt ./
RUN pip install -r requirements-plugins.txt

COPY . .

RUN mkdir -p /data/{recordings,config}

VOLUME /data/recordings
VOLUME /data/config

ENTRYPOINT [ "python", "main.py", "-O", "/data/recordings", "-C", "/data/config/config.yaml" ]