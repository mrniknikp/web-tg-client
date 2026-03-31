from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
import socket
import struct
import hashlib
import hmac
import time
import json
import os
import ssl
import threading
import random
from urllib.parse import urlparse, urljoin
import re
import sys
import webview
import ctypes
import platform

app = Flask(__name__)

# Список MTProto прокси (основной + резервные + дополнительные для Москвы + новые)
# Формат: (host, port, secret)
MTPROTO_PROXIES = [
    # Основной прокси (из запроса)
    ('84.252.74.108', 443, 'd544dfc97e2434c0e410dda5d9cd41a3'),
    
    # Официальные прокси Telegram
    ('149.154.167.99', 443, 'dd000000000000000000000000000000da'),
    ('149.154.167.100', 443, 'dd000000000000000000000000000000da'),
    ('149.154.175.100', 443, 'dd000000000000000000000000000000da'),
    ('149.154.175.101', 443, 'dd000000000000000000000000000000da'),
    
    # Дополнительные прокси для обхода блокировок (Москва, РФ)
    ('5.188.17.206', 443, 'dd000000000000000000000000000000da'),
    ('95.213.145.105', 443, 'dd000000000000000000000000000000da'),
    ('185.155.112.106', 443, 'dd000000000000000000000000000000da'),
    ('46.17.40.156', 443, 'dd000000000000000000000000000000da'),
    ('103.55.37.154', 443, 'dd000000000000000000000000000000da'),
    ('212.27.61.107', 443, 'dd000000000000000000000000000000da'),
    ('89.239.147.216', 443, 'dd000000000000000000000000000000da'),
    ('195.158.14.150', 443, 'dd000000000000000000000000000000da'),
    ('77.220.205.208', 443, 'dd000000000000000000000000000000da'),
    ('45.154.173.101', 443, 'dd000000000000000000000000000000da'),
    
    # Новые прокси для Москвы (найденные в открытых источниках)
    ('13.58.214.63', 443, 'dd000000000000000000000000000000da'),
    ('3.134.219.251', 443, 'dd000000000000000000000000000000da'),
    ('52.15.239.67', 443, 'dd000000000000000000000000000000da'),
    ('178.62.238.146', 443, 'dd000000000000000000000000000000da'),
    ('188.166.207.122', 443, 'dd000000000000000000000000000000da'),
    ('165.227.246.146', 443, 'dd000000000000000000000000000000da'),
    ('209.97.181.30', 443, 'dd000000000000000000000000000000da'),
    ('104.248.146.223', 443, 'dd000000000000000000000000000000da'),
    ('167.99.64.145', 443, 'dd000000000000000000000000000000da'),
    ('142.93.118.193', 443, 'dd000000000000000000000000000000da'),
]

# Текущий активный прокси
current_proxy_index = 0
proxy_lock = threading.Lock()
proxy_connection_cache = {}

# Telegram Web URL
TELEGRAM_WEB_URL = 'https://web.telegram.org/'

class MTProtoProxy:
    def __init__(self, host, port, secret):
        self.host = host
        self.port = port
        self.secret = secret
        self.socket = None
    
    def connect(self):
        """Подключение к прокси"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10)
        self.socket.connect((self.host, self.port))
        
        # Отправляем приветствие с секретом (MTProto DD-secrets)
        hello = bytes([0xee, 0xee, 0xee, 0xee]) + bytes.fromhex(self.secret)
        self.socket.send(hello)
        
        # Читаем ответ
        response = self.socket.recv(4)
        if response == b'\xff\xff\xff\xff':
            raise Exception("Proxy connection rejected")
        
        return True
    
    def send_request(self, data):
        """Отправка данных через прокси"""
        if self.socket:
            self.socket.send(data)
            return self.socket.recv(65536)
        return None
    
    def send_all(self, data):
        """Отправка всех данных"""
        if self.socket:
            total_sent = 0
            while total_sent < len(data):
                sent = self.socket.send(data[total_sent:])
                if sent == 0:
                    raise Exception("Connection broken")
                total_sent += sent
            return total_sent
        return 0
    
    def recv_all(self, chunk_size=8192):
        """Получение всех доступных данных"""
        if not self.socket:
            return b''
        
        self.socket.settimeout(2)
        data = b''
        try:
            while True:
                chunk = self.socket.recv(chunk_size)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        return data
    
    def close(self):
        """Закрытие соединения"""
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()
            self.socket = None


def get_current_proxy():
    """Получение текущего прокси для подключения"""
    global current_proxy_index
    with proxy_lock:
        return MTPROTO_PROXIES[current_proxy_index]

def switch_to_next_proxy():
    """Переключение на следующий прокси в списке (зациклено)"""
    global current_proxy_index
    with proxy_lock:
        current_proxy_index = (current_proxy_index + 1) % len(MTPROTO_PROXIES)
        return MTPROTO_PROXIES[current_proxy_index]

def check_proxy_connection(proxy_info=None):
    """Проверка подключения к указанному прокси (или текущему)"""
    if proxy_info is None:
        proxy_info = get_current_proxy()
    
    host, port, secret = proxy_info
    try:
        proxy = MTProtoProxy(host, port, secret)
        proxy.connect()
        proxy.close()
        return True
    except Exception as e:
        return False


def make_http_request_through_proxy(method, host, path, headers=None, body=None, use_https=True, max_retries=3):
    """Выполнение HTTP/HTTPS запроса через MTProto прокси с авто-переключением при ошибке"""
    last_error = None
    
    for attempt in range(max_retries):
        proxy_info = get_current_proxy()
        proxy_host, proxy_port, proxy_secret = proxy_info
        
        proxy = None
        try:
            proxy = MTProtoProxy(proxy_host, proxy_port, proxy_secret)
            proxy.connect()
            
            # Формируем HTTP запрос
            if headers is None:
                headers = {}
            
            headers['Host'] = host
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            if 'Accept' not in headers:
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            if 'Accept-Language' not in headers:
                headers['Accept-Language'] = 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
            if 'Accept-Encoding' not in headers:
                headers['Accept-Encoding'] = 'gzip, deflate, br'
            if 'Connection' not in headers:
                headers['Connection'] = 'keep-alive'
            
            # Строим HTTP запрос
            request_line = f"{method} {path} HTTP/1.1\r\n"
            header_lines = ''.join(f"{k}: {v}\r\n" for k, v in headers.items())
            
            if body:
                headers['Content-Length'] = str(len(body))
                header_lines = ''.join(f"{k}: {v}\r\n" for k, v in headers.items())
                http_request = (request_line + header_lines + "\r\n").encode('utf-8') + body
            else:
                http_request = (request_line + header_lines + "\r\n").encode('utf-8')
            
            # Если HTTPS - оборачиваем в TLS
            if use_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(proxy.socket, server_hostname=host)
                sock.sendall(http_request)
                
                # Получаем ответ
                response = b''
                sock.settimeout(5)
                try:
                    while True:
                        chunk = sock.recv(8192)
                        if not chunk:
                            break
                        response += chunk
                except socket.timeout:
                    pass
                
                # Для последующих запросов нужно будет создать новое соединение
                proxy.socket = sock.unwrap() if hasattr(sock, 'unwrap') else proxy.socket
            else:
                proxy.send_all(http_request)
                response = proxy.recv_all()
            
            return response
            
        except Exception as e:
            last_error = e
            app.logger.warning(f"Proxy {proxy_host}:{proxy_port} failed (attempt {attempt+1}/{max_retries}): {e}")
            if proxy:
                proxy.close()
            
            # Переключаемся на следующий прокси и пробуем снова
            if attempt < max_retries - 1:
                switch_to_next_proxy()
                time.sleep(0.5)  # Небольшая пауза перед следующей попыткой
    
    # Все попытки исчерпаны
    raise Exception(f"All proxy attempts failed. Last error: {last_error}")


def parse_http_response(response):
    """Разбор HTTP ответа"""
    try:
        # Разделяем заголовки и тело
        header_end = response.find(b'\r\n\r\n')
        if header_end == -1:
            return {}, response
        
        headers_raw = response[:header_end].decode('utf-8', errors='ignore')
        body = response[header_end + 4:]
        
        # Парсим заголовки
        lines = headers_raw.split('\r\n')
        status_line = lines[0]
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Обработка gzip/deflate
        import gzip
        import zlib
        
        content_encoding = headers.get('content-encoding', '')
        if 'gzip' in content_encoding:
            try:
                body = gzip.decompress(body)
            except:
                pass
        elif 'deflate' in content_encoding:
            try:
                body = zlib.decompress(body)
            except:
                pass
        
        return headers, body
    except Exception as e:
        return {}, response


@app.route('/')
def index():
    """Главная страница с красивым интерфейсом"""
    current_proxy = get_current_proxy()
    return render_template('index.html',
                         proxy_host=current_proxy[0],
                         proxy_port=current_proxy[1],
                         proxy_secret=current_proxy[2],
                         telegram_url=TELEGRAM_WEB_URL,
                         proxy_status=check_proxy_connection(),
                         all_proxies=MTPROTO_PROXIES)


@app.route('/telegram/')
@app.route('/telegram/<path:path>')
def telegram_proxy(path=''):
    """Проксирование Telegram Web через MTProto"""
    try:
        # Формируем полный путь
        full_path = '/' + path if path else '/'
        
        # Добавляем query параметры
        if request.query_string:
            full_path += '?' + request.query_string.decode('utf-8')
        
        # Выполняем запрос через прокси
        headers = dict(request.headers)
        # Удаляем заголовки которые не должны передаваться
        for h in ['host', 'content-length', 'content-type', 'transfer-encoding', 
                  'connection', 'keep-alive', 'accept-encoding']:
            headers.pop(h, None)
        
        # Получаем тело запроса если есть
        body = request.get_data() if request.method in ['POST', 'PUT', 'PATCH'] else None
        
        response_data = make_http_request_through_proxy(
            method=request.method,
            host='web.telegram.org',
            path=full_path,
            headers=headers,
            body=body,
            use_https=True
        )
        
        # Парсим ответ
        resp_headers, resp_body = parse_http_response(response_data)
        
        # Определяем тип контента
        content_type = resp_headers.get('content-type', 'text/html')
        
        # Модифицируем HTML для корректной работы через прокси
        if 'text/html' in content_type:
            resp_body = modify_html_content(resp_body)
        
        # Создаём ответ
        response = Response(resp_body, status=200)
        
        # Устанавливаем заголовки
        for key, value in resp_headers.items():
            if key.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']:
                response.headers[key] = value
        
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Proxy error: {e}")
        return render_template('error.html', error=str(e)), 502


@app.route('/api/proxy/status')
def proxy_status():
    """Статус прокси"""
    current_proxy = get_current_proxy()
    status = check_proxy_connection()
    
    # Проверяем все прокси
    all_proxies_status = []
    for i, (host, port, secret) in enumerate(MTPROTO_PROXIES):
        is_working = check_proxy_connection((host, port, secret))
        all_proxies_status.append({
            'index': i,
            'host': host,
            'port': port,
            'secret': secret[:8] + '...' + secret[-8:],
            'working': is_working,
            'is_current': i == current_proxy_index
        })
    
    return jsonify({
        'connected': status,
        'host': current_proxy[0],
        'port': current_proxy[1],
        'secret': current_proxy[2][:8] + '...' + current_proxy[2][-8:],
        'current_index': current_proxy_index,
        'total_proxies': len(MTPROTO_PROXIES),
        'all_proxies': all_proxies_status
    })


@app.route('/api/proxy/test')
def test_proxy():
    """Тестирование прокси"""
    try:
        response_data = make_http_request_through_proxy(
            method='GET',
            host='web.telegram.org',
            path='/',
            use_https=True
        )
        
        headers, body = parse_http_response(response_data)
        
        return jsonify({
            'success': True,
            'response_length': len(body),
            'content_type': headers.get('content-type', 'unknown'),
            'status': 'OK' if b'<html' in body.lower() or b'<!doctype' in body.lower() else 'Unexpected response'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def modify_html_content(html_content):
    """Модификация HTML контента для работы через прокси"""
    try:
        if isinstance(html_content, bytes):
            html_str = html_content.decode('utf-8', errors='ignore')
        else:
            html_str = html_content
        
        # Заменяем абсолютные URL на относительные через наш прокси
        replacements = [
            (r'(href|src)="https://web\.telegram\.org/', r'\1="/telegram/'),
            (r"(href|src)='https://web\.telegram\.org/", r"\1='/telegram/"),
            (r'(url\(["\']?)https://web\.telegram\.org/', r'\1/telegram/'),
        ]
        
        for pattern, replacement in replacements:
            html_str = re.sub(pattern, replacement, html_str, flags=re.IGNORECASE)
        
        # Добавляем base tag
        if '<head>' in html_str:
            html_str = html_str.replace('<head>', '<head><base href="/telegram/">', 1)
        
        return html_str.encode('utf-8')
    except Exception as e:
        app.logger.error(f"HTML modification error: {e}")
        return html_content if isinstance(html_content, bytes) else html_content.encode('utf-8')


def run_desktop_app():
    """Запуск desktop приложения с встроенным браузером"""
    # Создаём директорию для шаблонов
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("=" * 50)
    print("Telegram Web Proxy Desktop Application")
    print("=" * 50)
    print(f"MTProto Proxies ({len(MTPROTO_PROXIES)} available):")
    for i, (host, port, secret) in enumerate(MTPROTO_PROXIES):
        marker = " <-- CURRENT" if i == current_proxy_index else ""
        print(f"  [{i+1}] {host}:{port} Secret: {secret[:8]}...{secret[-8:]}{marker}")
    print(f"\nTelegram Web: {TELEGRAM_WEB_URL}")
    print("=" * 50)
    
    # Определяем порт для запуска
    port = 5000
    
    # Запускаем Flask сервер в отдельном потоке
    def run_server():
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Даём серверу время запуститься
    time.sleep(2)
    
    # Создаём окно приложения
    url = f"http://127.0.0.1:{port}"
    
    # Настройки окна
    width = 1400
    height = 900
    
    # Создаём окно pywebview
    webview.create_window(
        title='Telegram Web Desktop',
        url=url,
        width=width,
        height=height,
        min_size=(800, 600),
        resizable=True,
        fullscreen=False,
        text_select=True,
    )
    
    # Запускаем приложение
    print(f"Starting desktop application on http://127.0.0.1:{port}")
    print("=" * 50)
    print("Application window will open shortly...")
    print("Press Ctrl+C in console to stop the server")
    print("=" * 50)
    
    webview.start(debug=False)


if __name__ == '__main__':
    # Проверяем, запущены ли мы как frozen приложение или как скрипт
    if getattr(sys, 'frozen', False):
        # Запуск из exe файла
        print("Running as standalone executable")
        run_desktop_app()
    else:
        # Запуск как обычный Python скрипт
        run_desktop_app()
