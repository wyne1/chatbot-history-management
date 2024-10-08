// script.js

document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

let totalTokenCount = 0;

function addMessage(role, content) {
    const chatWindow = document.getElementById('chat-window');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', role);
    messageDiv.textContent = `${role.charAt(0).toUpperCase() + role.slice(1)}: ${content}`;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const messageText = userInput.value.trim();
    if (messageText === '') return;

    addMessage('user', messageText);
    userInput.value = '';

    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: 'user1', message_text: messageText }),
    });

    const data = await response.json();
    addMessage('assistant', data.response);

    totalTokenCount += data.token_count;
    document.getElementById('token-count').textContent = `Total Tokens Used: ${totalTokenCount}`;
}