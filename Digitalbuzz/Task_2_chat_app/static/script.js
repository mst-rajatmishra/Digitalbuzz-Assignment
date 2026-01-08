let socket;
let currentRoomId;

function initChat(roomId, userId, username) {
    currentRoomId = roomId;
    
    // Connect to Socket.IO server
    socket = io();
    
    // Join the room
    socket.emit('join', { room_id: roomId });
    
    // Set up UI event listeners
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('message-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    document.getElementById('image-btn').addEventListener('click', function() {
        document.getElementById('image-input').click();
    });
    
    document.getElementById('image-input').addEventListener('change', handleImageUpload);
    document.getElementById('leave-room').addEventListener('click', leaveRoom);
    document.getElementById('back-btn').addEventListener('click', goBackToRooms);
    
    // Handle incoming messages
    socket.on('new_message', function(data) {
        addMessageToUI(data);
        scrollToBottom();
    });
    
    // Handle notifications
    socket.on('notification', function(data) {
        showNotification(data.message, data.type);
    });
    
    // Handle errors
    socket.on('error', function(data) {
        showNotification(data.message, 'error');
    });
    
    // Handle user list updates
    socket.on('user_list_update', function(data) {
        updateUserList(data.users, data.count);
    });
    
    // Scroll to bottom initially
    scrollToBottom();
}

function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (message) {
        socket.emit('message', {
            room_id: currentRoomId,
            content: message,
            content_type: 'text'
        });
        input.value = '';
    }
}

function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(event) {
        const imageData = event.target.result;
        socket.emit('image', {
            room_id: currentRoomId,
            image: imageData
        });
    };
    reader.readAsDataURL(file);
    
    // Clear input
    e.target.value = '';
}

function addMessageToUI(message) {
    const messagesContainer = document.getElementById('chat-messages');
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    
    const messageHeader = document.createElement('div');
    messageHeader.classList.add('message-header');
    
    const username = document.createElement('strong');
    username.textContent = message.username;
    
    const timestamp = document.createElement('span');
    const date = new Date(message.timestamp);
    timestamp.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageHeader.appendChild(username);
    messageHeader.appendChild(timestamp);
    
    messageElement.appendChild(messageHeader);
    
    if (message.content_type === 'text') {
        const content = document.createElement('p');
        content.textContent = message.content;
        messageElement.appendChild(content);
    } else {
        const image = document.createElement('img');
        image.src = message.content;
        image.alt = "Shared image";
        image.classList.add('chat-image');
        messageElement.appendChild(image);
    }
    
    messagesContainer.appendChild(messageElement);
}

function showNotification(message, type) {
    const notificationArea = document.getElementById('notification-area');
    
    const notification = document.createElement('div');
    notification.classList.add('notification', type);
    notification.textContent = message;
    
    notificationArea.appendChild(notification);
    
    // Auto-remove notification after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
    
    // Scroll to bottom of notifications
    notificationArea.scrollTop = notificationArea.scrollHeight;
}

function leaveRoom() {
    socket.emit('leave', { room_id: currentRoomId });
    goBackToRooms();
}

function goBackToRooms() {
    window.location.href = '/chat';
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateUserList(users, count) {
    // Update active count
    const activeCountEl = document.getElementById('active-count');
    if (activeCountEl) {
        activeCountEl.textContent = count;
    }
    
    // Update user list
    const userListEl = document.getElementById('active-users-list');
    if (userListEl) {
        userListEl.innerHTML = '';
        users.forEach(function(username) {
            const userItem = document.createElement('div');
            userItem.classList.add('user-item');
            userItem.innerHTML = '<span class="user-dot">●</span> ' + username;
            userListEl.appendChild(userItem);
        });
    }
}