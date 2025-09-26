FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости сначала (для кэширования)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальное приложение
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Создаем директории
RUN mkdir -p /app/logs

CMD ["sh", "-c", "alembic upgrade head && python -m app"]влл