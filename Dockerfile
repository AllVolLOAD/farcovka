FROM python:3.11-slim

WORKDIR /app

# Устанавливаем часовой пояс
RUN apt-get update && apt-get install -y tzdata
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем папку для логов
RUN mkdir -p logs

CMD ["python", "-m", "app"]
