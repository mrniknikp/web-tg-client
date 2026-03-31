# Telegram Web через MTProto Proxy

Приложение для доступа к настоящему веб-интерфейсу Telegram (web.telegram.org) через MTProto прокси.

## Особенности

- 🔐 **Безопасное соединение** - весь трафик идёт через MTProto прокси
- 🌐 **Настоящий Telegram** - полноценный веб-интерфейс web.telegram.org
- 🎨 **Красивый интерфейс** - современный дизайн в стиле Telegram Dark
- ⚡ **Быстрая загрузка** - прямое подключение через прокси

## Настройки прокси

По умолчанию используется жёстко заданный MTProto прокси:

```python
PROXY_HOST = '84.252.74.108'
PROXY_PORT = 443
PROXY_SECRET = 'd544dfc97e2434c0e410dda5d9cd41a3'
```

Для изменения прокси отредактируйте эти значения в `app.py`.

## Установка и запуск

### Требования

- Python 3.8+
- Flask

### Установка зависимостей

```bash
pip install flask
```

### Запуск сервера

```bash
python app.py
```

Сервер запустится на адресе `http://0.0.0.0:5000`

## Использование

1. Откройте браузер и перейдите на `http://localhost:5000`
2. Нажмите кнопку "🚀 Запустить Telegram Web"
3. Войдите в свой аккаунт Telegram
4. Пользуйтесь полноценным Telegram через прокси!

## Структура проекта

```
├── app.py              # Основной сервер Flask
├── templates/
│   ├── index.html      # Главная страница
│   └── error.html      # Страница ошибки
├── static/
│   ├── style.css       # Стили
│   └── script.js       # JavaScript
└── README.md           # Этот файл
```

## API endpoints

- `GET /` - Главная страница
- `GET /telegram/*` - Проксирование Telegram Web
- `GET /api/proxy/status` - Статус подключения к прокси
- `GET /api/proxy/test` - Тестирование прокси

## Технологии

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Proxy**: MTProto (DD-secrets format)
- **TLS**: SSL/TLS обёртка для HTTPS запросов

## Примечания

- Приложение использует MTProto proxy с DD-secrets форматом
- Для работы необходим доступ к указанному прокси-серверу
- Все запросы к Telegram проходят через прокси для обеспечения приватности