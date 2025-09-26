FROM python:3.11-slim-buster as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim-buster

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app app

ENV PATH=/root/.local/bin:$PATH
VOLUME /log /config
EXPOSE 3000

ENTRYPOINT ["python", "-m", "app"]
