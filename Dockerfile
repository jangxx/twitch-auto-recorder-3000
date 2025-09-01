FROM python:3.13

WORKDIR /opt/twitch-auto-recorder-3000

RUN apt-get update
RUN apt-get install -y ffmpeg build-essential

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY requirements-plugins.txt ./
RUN pip install -r requirements-plugins.txt

COPY . .

RUN mkdir -p /data/recordings

RUN touch /data/config.yaml

VOLUME /data/recordings

ENTRYPOINT [ "python", "main.py", "-O", "/data/recordings", "-C", "/data/config.yaml" ]