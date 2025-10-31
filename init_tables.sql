-- Инициализация таблиц для FarCovka бота
-- Выполнить: docker exec -i farcovka_db psql -U postgres -d facovka00 -f init_tables.sql

-- Таблица курсов валют
CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    pair VARCHAR NOT NULL UNIQUE,
    buy_rate FLOAT NOT NULL,
    sell_rate FLOAT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_admin_id BIGINT
);

-- Таблица очереди пользователей
CREATE TABLE IF NOT EXISTS queue_entries (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN DEFAULT FALSE
);

-- Текущие курсы
CREATE TABLE IF NOT EXISTS current_rates (
    id SERIAL PRIMARY KEY,
    rate_value FLOAT NOT NULL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_admin_id BIGINT
);

-- История курсов
CREATE TABLE IF NOT EXISTS rate_history (
    id SERIAL PRIMARY KEY,
    rate_value FLOAT NOT NULL,
    admin_id BIGINT,
    user_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индексы для производительности
CREATE INDEX IF NOT EXISTS idx_exchange_rates_pair ON exchange_rates(pair);
CREATE INDEX IF NOT EXISTS idx_queue_entries_processed ON queue_entries(is_processed);
CREATE INDEX IF NOT EXISTS idx_queue_entries_created ON queue_entries(created_at);

-- Выводим список созданных таблиц
SELECT '✅ Таблицы созданы успешно!' as message;
SELECT table_name as "Созданные таблицы:" 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
