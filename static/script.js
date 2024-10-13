// script.js

document.getElementById('send-button').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
document.getElementById('approach-selector').addEventListener('change', changeApproach);

async function changeApproach() {
    const approach = document.getElementById('approach-selector').value;
    const response = await fetch('/change_approach', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ approach: approach }),
    });
    const data = await response.json();
    console.log('Approach changed to:', data.new_approach);
}

let totalTokenCount = 0;
const userId = 'user3';  // Assuming a fixed user_id for now

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
        body: JSON.stringify({ user_id: userId, message_text: messageText }),
    });

    const data = await response.json();
    addMessage('assistant', data.response);

    totalTokenCount += data.token_count;
    document.getElementById('token-count').textContent = `Total Tokens Used: ${totalTokenCount}`;

    // Fetch and display Redis and MongoDB data
    fetchData();
}

async function fetchData() {
    // Fetch Redis data
    const redisResponse = await fetch(`/redis_data/${userId}`);
    const redisData = await redisResponse.json();
    document.getElementById('redis-data').textContent = JSON.stringify(redisData, null, 2);

    // Fetch MongoDB data
    const mongodbResponse = await fetch(`/mongodb_data/${userId}`);
    const mongodbData = await mongodbResponse.json();
    document.getElementById('mongodb-data').textContent = JSON.stringify(mongodbData, null, 2);
}



// async function fetchData() {
//     const userId = 'user3'; // Replace with actual user ID management

//     // Fetch internal state data
//     const internalStateResponse = await fetch(`/internal_state/${userId}`);
//     const internalStateData = await internalStateResponse.json();

//     // Display internal state data
//     displayInternalState(internalStateData);
// }

// function displayInternalState(data) {
//     const container = document.getElementById('internal-state-container');
//     container.innerHTML = ''; // Clear previous content

//     for (const [key, value] of Object.entries(data)) {
//         const section = document.createElement('div');
//         section.className = 'internal-state-section';
//         section.innerHTML = `
//             <h3>${key}</h3>
//             <pre>${JSON.stringify(value, null, 2)}</pre>
//         `;
//         container.appendChild(section);
//     }
// }

// Fetch data initially when the page loads
fetchData();