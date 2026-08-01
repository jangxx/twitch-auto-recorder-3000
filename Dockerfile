FROM python:3.13-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_NO_DEV=1

WORKDIR /opt/twitch-auto-recorder-3000

RUN apt-get update
RUN apt-get install -y ffmpeg build-essential chromium

COPY . .
RUN uv sync --locked

RUN mkdir -p /data/recordings

RUN touch /data/config.yaml

VOLUME /data/recordings

ENTRYPOINT [ "uv", "run", "main.py", "-O", "/data/recordings", "-C", "/data/config.yaml" ]