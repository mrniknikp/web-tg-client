// Проверка статуса прокси при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkProxyStatus();
    setInterval(checkProxyStatus, 30000); // Проверка каждые 30 секунд
});

// Проверка статуса прокси
async function checkProxyStatus() {
    try {
        const response = await fetch('/api/proxy/status');
        const data = await response.json();
        
        updateProxyStatus(data.connected);
    } catch (error) {
        console.error('Ошибка проверки статуса прокси:', error);
        updateProxyStatus(false);
    }
}

// Обновление отображения статуса прокси
function updateProxyStatus(connected) {
    const proxyStatus = document.getElementById('proxyStatus');
    const connectionStatus = document.getElementById('connectionStatus');
    
    if (connected) {
        proxyStatus.querySelector('.status-indicator').style.backgroundColor = '#4caf50';
        proxyStatus.querySelector('.status-text').textContent = 'Прокси подключен';
        
        connectionStatus.querySelector('.status-dot').style.backgroundColor = '#4caf50';
        connectionStatus.querySelector('span:last-child').textContent = 'Подключено';
    } else {
        proxyStatus.querySelector('.status-indicator').style.backgroundColor = '#f44336';
        proxyStatus.querySelector('.status-text').textContent = 'Прокси отключен';
        
        connectionStatus.querySelector('.status-dot').style.backgroundColor = '#f44336';
        connectionStatus.querySelector('span:last-child').textContent = 'Отключено';
    }
}

// Тестирование прокси
async function testProxy() {
    const btn = document.querySelector('.test-proxy-btn');
    btn.disabled = true;
    btn.textContent = 'Тестирование...';
    
    try {
        const response = await fetch('/api/proxy/test');
        const data = await response.json();
        
        if (data.success) {
            alert('✓ Прокси работает корректно!\nОтвет сервера: ' + data.response_length + ' байт');
            updateProxyStatus(true);
        } else {
            alert('✗ Ошибка подключения к прокси:\n' + data.error);
            updateProxyStatus(false);
        }
    } catch (error) {
        alert('✗ Ошибка тестирования прокси:\n' + error.message);
        updateProxyStatus(false);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Тестировать прокси';
    }
}

// Обработка отправки сообщения
const messageField = document.querySelector('.message-field');
const sendBtn = document.querySelector('.send-btn');

messageField.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

function sendMessage() {
    const text = messageField.value.trim();
    if (text) {
        // Здесь будет логика отправки сообщения через прокси
        console.log('Отправка сообщения:', text);
        messageField.value = '';
        
        // Добавляем сообщение в чат (демонстрация)
        addMessageToChat(text, 'outgoing');
    }
}

// Добавление сообщения в чат
function addMessageToChat(text, type) {
    const messagesContainer = document.getElementById('messagesContainer');
    
    // Удаляем приветственное сообщение если оно есть
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.style.cssText = `
        max-width: 60%;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 12px;
        background-color: ${type === 'outgoing' ? '#2b5278' : '#17212b'};
        align-self: ${type === 'outgoing' ? 'flex-end' : 'flex-start'};
    `;
    messageDiv.textContent = text;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Анимация чатов при клике
const chatItems = document.querySelectorAll('.chat-item');
chatItems.forEach(item => {
    item.addEventListener('click', function() {
        chatItems.forEach(i => i.classList.remove('active'));
        this.classList.add('active');
        
        // Обновляем заголовок чата
        const chatName = this.querySelector('.chat-name').textContent;
        document.querySelector('.chat-header-info h3').textContent = chatName;
    });
});
