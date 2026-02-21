# SERP Analyzer (MVP)

Минимальный MVP-сервис для почасового мониторинга Google SERP и SEO-тегов.

## Быстрый старт

1) Создать и заполнить `.env` из примера:

```bash
cp .env.example .env
```

2) Установить зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

3) Запуск CLI:

```bash
hourly-run --config configs/keywords.yaml
export-csv --out out/results.csv
```

## Команды CLI

- `hourly-run` — выполняет один почасовой прогон (SERP)
- `export-csv` — экспортирует результаты в CSV

## Структура проекта (основа)

- `src/serp_monitor/db/models` — модели БД
- `src/serp_monitor/services` — доменные сервисы
- `src/serp_monitor/parsers` — парсеры HTML/SEO-тегов
- `src/serp_monitor/providers` — провайдеры SERP
- `src/serp_monitor/worker` — планировщик/фоновые задачи
- `src/serp_monitor/cli` — CLI-точки входа
- `src/serp_monitor/config` — конфиги приложения
- `src/serp_monitor/utils` — утилиты
