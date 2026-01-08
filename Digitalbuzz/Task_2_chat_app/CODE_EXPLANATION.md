# Task 2 Chat Application - Complete Code Explanation

## Overview
This is a real-time group chat application built with Flask and Socket.IO. It supports multiple chat rooms, real-time messaging, image sharing, and user presence tracking.

---

## File Structure

```
Task_2_chat_app/
├── app.py                 # Main Flask application with routes and SocketIO handlers
├── models.py              # Database models (User, Room, Message, RoomMember)
├── setup_db.py            # Database initialization script
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── START_CHAT_APP.bat     # Windows batch file to start the app
├── static/
│   ├── script.js          # Client-side JavaScript for real-time chat
│   └── style.css          # CSS styling for the application
└── templates/
    ├── login.html         # Login page template
    ├── index.html         # Main chat page (room list)
    └── room.html          # Chat room page template
```

---

## 1. app.py - Main Application File

### Lines 1-9: Import Statements
```python
import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, User, Room, Message, RoomMember
from dotenv import load_dotenv
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
```
- **Line 1**: Import `os` for environment variable access
- **Line 2**: Import Flask components for web routing and templating
- **Line 3**: Import Socket.IO components for real-time WebSocket communication
- **Line 4**: Import database models (User, Room, Message, RoomMember)
- **Line 5**: Import `load_dotenv` to load environment variables from .env file
- **Line 6**: Import `datetime` for timestamp handling
- **Lines 7-9**: Import libraries for image processing (base64 encoding/decoding, PIL)

### Lines 11-12: Load Environment Variables
```python
load_dotenv()
```
- Loads environment variables from `.env` file (DATABASE_URL, SECRET_KEY)

### Lines 14-21: Application Factory Function
```python
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.getenv('SECRET_KEY')
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    db.init_app(app)
    return app
```
- **Line 14**: Define application factory pattern for better testing and modularity
- **Line 15**: Create Flask application instance
- **Line 16**: Configure database connection string from environment variable
- **Line 17**: Disable SQLAlchemy modification tracking (improves performance)
- **Line 18**: Set secret key for session encryption from environment variable
- **Line 19**: Configure upload folder for potential file uploads
- **Line 20**: Initialize database with the Flask app
- **Line 21**: Return configured application

### Lines 23-24: Initialize Application and Socket.IO
```python
app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")
```
- **Line 23**: Create application instance
- **Line 24**: Initialize Socket.IO with CORS enabled for all origins (allows real-time connections)

### Lines 26-27: Track Active Users
```python
active_users = {}  # {room_id: {session_id: username}}
```
- Global dictionary to track which users are active in each room
- Structure: `{room_id: {socket_session_id: username}}`

### Lines 29-33: Home Route
```python
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))
```
- **Line 29**: Define root URL route
- **Line 31**: Check if user is logged in (username in session)
- **Line 32**: If logged in, redirect to chat page
- **Line 33**: If not logged in, redirect to login page

### Lines 35-51: Login Route
```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        
        # Check if user exists or create new
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        
        session['username'] = username
        session['user_id'] = user.id
        return redirect(url_for('chat'))
    
    return render_template('login.html')
```
- **Line 35**: Define login route accepting GET and POST methods
- **Line 37**: Check if request is POST (form submission)
- **Line 38**: Get username from form data
- **Line 41**: Query database for existing user with this username
- **Lines 42-45**: If user doesn't exist, create new user and save to database
- **Lines 47-48**: Store username and user_id in session (server-side storage)
- **Line 49**: Redirect to chat page after successful login
- **Line 51**: For GET requests, render login template

### Lines 53-62: Chat Page Route
```python
@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    rooms = Room.query.all()
    return render_template('index.html', 
                           username=session['username'], 
                           rooms=rooms,
                           user_id=session['user_id'])
```
- **Line 53**: Define chat route (main page with room list)
- **Lines 55-56**: Check authentication - redirect to login if not logged in
- **Line 58**: Get all available chat rooms from database
- **Lines 59-62**: Render index.html with username, rooms list, and user_id

### Lines 64-84: Room Page Route
```python
@app.route('/room/<int:room_id>')
def room(room_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    room = Room.query.get_or_404(room_id)
    messages = Message.query.filter_by(room_id=room_id).order_by(Message.timestamp.desc()).limit(20).all()
    messages.reverse()  # Show oldest first
    
    # Add user to room if not already a member
    member = RoomMember.query.filter_by(user_id=session['user_id'], room_id=room_id).first()
    if not member:
        member = RoomMember(user_id=session['user_id'], room_id=room_id)
        db.session.add(member)
        db.session.commit()
    
    return render_template('room.html', 
                           room=room, 
                           messages=messages,
                           username=session['username'],
                           user_id=session['user_id'])
```
- **Line 64**: Define room route with room_id as URL parameter
- **Lines 66-67**: Check authentication
- **Line 69**: Get room by ID or return 404 if not found
- **Line 70**: Get last 20 messages for this room, ordered by timestamp (newest first)
- **Line 71**: Reverse list to show oldest messages first (chronological order)
- **Lines 74-78**: Check if user is already a room member, if not create membership record
- **Lines 80-84**: Render room.html with room data, messages, username, and user_id

### Lines 86-107: Get Messages API Route
```python
@app.route('/messages/<int:room_id>')
def get_messages(room_id):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    messages = Message.query.filter_by(room_id=room_id)\
        .order_by(Message.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    messages_list = [{
        'id': msg.id,
        'content': msg.content,
        'content_type': msg.content_type,
        'timestamp': msg.timestamp.isoformat(),
        'username': msg.user.username
    } for msg in messages.items]
    
    return jsonify({
        'messages': messages_list,
        'has_next': messages.has_next,
        'has_prev': messages.has_prev
    })
```
- **Line 86**: Define API endpoint to get messages for pagination
- **Line 88**: Get page number from query parameters (default: 1)
- **Line 89**: Set messages per page to 20
- **Lines 91-93**: Query messages with pagination support
- **Lines 95-101**: Convert message objects to dictionary format (JSON serializable)
- **Lines 103-107**: Return JSON response with messages and pagination info

### Lines 109-112: Socket.IO Connect Event
```python
@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        print(f"User {session['username']} connected")
```
- **Line 109**: Handle when a client establishes WebSocket connection
- **Line 111**: Check if user is authenticated
- **Line 112**: Log connection event to console

### Lines 114-137: Socket.IO Disconnect Event
```python
@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        print(f"User {session['username']} disconnected")
        
        # Remove user from all rooms they were in
        for room_id in list(active_users.keys()):
            if request.sid in active_users[room_id]:
                username = active_users[room_id][request.sid]
                del active_users[room_id][request.sid]
                
                # Get updated list
                users_in_room = list(active_users[room_id].values())
                
                # Broadcast to room
                emit('notification', {
                    'message': f"{username} has disconnected",
                    'type': 'leave'
                }, room=room_id)
                
                emit('user_list_update', {
                    'users': users_in_room,
                    'count': len(users_in_room)
                }, room=room_id)
```
- **Line 114**: Handle when a client disconnects
- **Line 116**: Check if user was authenticated
- **Line 117**: Log disconnection
- **Line 120**: Loop through all rooms to find where user was active
- **Line 121**: Check if this socket session was in the room
- **Line 122**: Get username from active_users
- **Line 123**: Remove user from active_users tracking
- **Line 126**: Get updated list of users still in room
- **Lines 129-132**: Broadcast notification that user disconnected
- **Lines 134-137**: Broadcast updated user list to everyone in room

### Lines 139-163: Socket.IO Join Room Event
```python
@socketio.on('join')
def handle_join(data):
    room_id = str(data['room_id'])
    join_room(room_id)
    print(f"User {session['username']} joined room {room_id}")
    
    # Track active user
    if room_id not in active_users:
        active_users[room_id] = {}
    active_users[room_id][request.sid] = session['username']
    
    # Get list of users in room
    users_in_room = list(active_users[room_id].values())
    
    # Broadcast notification
    emit('notification', {
        'message': f"{session['username']} has joined the room",
        'type': 'join'
    }, room=room_id)
    
    # Broadcast updated user list to everyone in room
    emit('user_list_update', {
        'users': users_in_room,
        'count': len(users_in_room)
    }, room=room_id)
```
- **Line 139**: Handle when user joins a room
- **Line 141**: Get room_id from client data and convert to string
- **Line 142**: Add socket to Socket.IO room (enables broadcasting to room)
- **Line 143**: Log join event
- **Lines 146-148**: Initialize room in active_users if needed
- **Line 149**: Add user to active_users tracking
- **Line 152**: Get list of all active users in room
- **Lines 155-158**: Broadcast join notification to all users in room
- **Lines 161-163**: Broadcast updated user list with count

### Lines 165-188: Socket.IO Leave Room Event
```python
@socketio.on('leave')
def handle_leave(data):
    room_id = str(data['room_id'])
    leave_room(room_id)
    print(f"User {session['username']} left room {room_id}")
    
    # Remove user from active users
    if room_id in active_users and request.sid in active_users[room_id]:
        del active_users[room_id][request.sid]
    
    # Get updated list
    users_in_room = list(active_users.get(room_id, {}).values())
    
    # Broadcast notification
    emit('notification', {
        'message': f"{session['username']} has left the room",
        'type': 'leave'
    }, room=room_id)
    
    # Broadcast updated user list
    emit('user_list_update', {
        'users': users_in_room,
        'count': len(users_in_room)
    }, room=room_id)
```
- **Line 165**: Handle when user leaves a room
- **Line 167**: Get room_id from client data
- **Line 168**: Remove socket from Socket.IO room
- **Line 169**: Log leave event
- **Lines 172-173**: Remove user from active_users tracking
- **Line 176**: Get updated list of remaining users
- **Lines 179-182**: Broadcast leave notification
- **Lines 185-188**: Broadcast updated user list

### Lines 190-225: Socket.IO Message Event
```python
@socketio.on('message')
def handle_message(data):
    room_id = data['room_id']
    content = data['content']
    content_type = data.get('content_type', 'text')
    
    # Create message
    message = Message(
        content=content,
        content_type=content_type,
        user_id=session['user_id'],
        room_id=room_id
    )
    db.session.add(message)
    db.session.commit()
    
    # Broadcast message to room
    emit('new_message', {
        'id': message.id,
        'content': content,
        'content_type': content_type,
        'timestamp': message.timestamp.isoformat(),
        'username': session['username'],
        'user_id': session['user_id']
    }, room=room_id)
    
    # Send notification to room
    if content_type == 'text':
        notification = f"{session['username']}: {content[:30]}..."
    else:
        notification = f"{session['username']} sent an image"
        
    emit('notification', {
        'message': notification,
        'type': 'message'
    }, room=room_id)
```
- **Line 190**: Handle when user sends a message
- **Lines 192-194**: Extract room_id, content, and content_type from client data
- **Lines 197-203**: Create new Message object and save to database
- **Lines 204-205**: Add to session and commit to database
- **Lines 208-214**: Broadcast new message to all users in room with 'new_message' event
- **Lines 217-220**: Create notification text (truncate text messages to 30 chars)
- **Lines 222-225**: Broadcast notification event

### Lines 227-278: Socket.IO Image Event
```python
@socketio.on('image')
def handle_image(data):
    room_id = data['room_id']
    image_data = data['image']
    
    # Decode base64 image
    try:
        # Extract base64 data
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        # Process image
        img = Image.open(BytesIO(binary_data))
        img.thumbnail((800, 800))  # Resize to manageable dimensions
        
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        processed_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Create data URI
        processed_data = f"data:image/png;base64,{processed_image}"
        
        # Save message
        message = Message(
            content=processed_data,
            content_type='image',
            user_id=session['user_id'],
            room_id=room_id
        )
        db.session.add(message)
        db.session.commit()
        
        # Broadcast image to room
        emit('new_message', {
            'id': message.id,
            'content': processed_data,
            'content_type': 'image',
            'timestamp': message.timestamp.isoformat(),
            'username': session['username'],
            'user_id': session['user_id']
        }, room=room_id)
        
        # Send notification
        emit('notification', {
            'message': f"{session['username']} sent an image",
            'type': 'message'
        }, room=room_id)
        
    except Exception as e:
        print(f"Error processing image: {e}")
        emit('error', {'message': 'Failed to process image'})
```
- **Line 227**: Handle image upload event
- **Lines 229-230**: Extract room_id and image data
- **Line 233**: Start try block for error handling
- **Line 235**: Split data URI to get base64 encoded part
- **Line 236**: Decode base64 to binary data
- **Lines 239-240**: Open image with PIL and resize to max 800x800 (maintains aspect ratio)
- **Lines 243-245**: Save processed image to buffer and re-encode as base64
- **Line 248**: Create data URI string for image
- **Lines 251-258**: Create Message record with image data and save to database
- **Lines 261-268**: Broadcast new image message to all users in room
- **Lines 271-274**: Send notification about image
- **Lines 276-278**: Handle errors and emit error event to client

### Lines 280-281: Application Entry Point
```python
if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
```
- **Line 280**: Check if script is run directly (not imported)
- **Line 281**: Start Socket.IO server with debug mode and unsafe werkzeug (for development)

---

## 2. models.py - Database Models

### Lines 1-3: Initialize SQLAlchemy
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
```
- **Line 1**: Import SQLAlchemy ORM (Object-Relational Mapping)
- **Line 3**: Create database instance for use across the application

### Lines 5-10: User Model
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    
    messages = db.relationship('Message', backref='user', lazy=True)
    room_memberships = db.relationship('RoomMember', backref='user', lazy=True)
```
- **Line 5**: Define User model (maps to 'user' table in database)
- **Line 6**: Primary key column (auto-incrementing integer)
- **Line 7**: Username column (max 80 chars, must be unique, required)
- **Line 9**: One-to-many relationship: one user can have many messages
- **Line 10**: One-to-many relationship: one user can be member of many rooms

### Lines 12-17: Room Model
```python
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    messages = db.relationship('Message', backref='room', lazy=True)
    members = db.relationship('RoomMember', backref='room', lazy=True)
```
- **Line 12**: Define Room model (represents chat rooms)
- **Line 13**: Primary key
- **Line 14**: Room name (max 100 chars, required)
- **Line 16**: One-to-many: one room can have many messages
- **Line 17**: One-to-many: one room can have many members

### Lines 19-26: Message Model
```python
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), default='text')  # 'text' or 'image'
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
```
- **Line 19**: Define Message model (stores chat messages)
- **Line 20**: Primary key
- **Line 21**: Message content (Text field for large content, required)
- **Line 22**: Content type ('text' or 'image', defaults to 'text')
- **Line 23**: Timestamp (automatically set to current time by database)
- **Line 25**: Foreign key to User table (who sent the message)
- **Line 26**: Foreign key to Room table (which room message belongs to)

### Lines 28-31: RoomMember Model
```python
class RoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
```
- **Line 28**: Define RoomMember model (tracks which users are in which rooms)
- **Line 29**: Primary key
- **Line 30**: Foreign key to User table
- **Line 31**: Foreign key to Room table
- This creates a many-to-many relationship between Users and Rooms

---

## 3. setup_db.py - Database Setup Script

### Lines 1-2: Import Required Modules
```python
from models import db
from app import create_app
```
- Import database instance and application factory

### Lines 4-5: Create Application
```python
app = create_app()

with app.app_context():
```
- **Line 4**: Create Flask application instance
- **Line 6**: Enter application context (required for database operations)

### Line 7: Create Database Tables
```python
    db.create_all()
```
- Create all database tables based on model definitions

### Lines 9-15: Create Initial Rooms
```python
    from models import Room
    rooms = ['General', 'Tech Talk', 'Random']
    for room_name in rooms:
        if not Room.query.filter_by(name=room_name).first():
            new_room = Room(name=room_name)
            db.session.add(new_room)
```
- **Line 10**: Import Room model
- **Line 11**: List of default room names
- **Line 12**: Loop through room names
- **Line 13**: Check if room already exists (avoid duplicates)
- **Lines 14-15**: Create and add new room if it doesn't exist

### Lines 17-18: Commit and Confirm
```python
    db.session.commit()
    print("Database setup complete!")
```
- **Line 17**: Save all changes to database
- **Line 18**: Print confirmation message

---

## 4. static/script.js - Client-Side JavaScript

### Lines 1-2: Global Variables
```javascript
let socket;
let currentRoomId;
```
- **Line 1**: Will store Socket.IO connection object
- **Line 2**: Will store the current room ID user is in

### Lines 4-53: Initialize Chat Function
```javascript
function initChat(roomId, userId, username) {
    currentRoomId = roomId;
    
    // Connect to Socket.IO server
    socket = io();
    
    // Join the room
    socket.emit('join', { room_id: roomId });
```
- **Line 4**: Main initialization function called when entering a room
- **Line 5**: Store current room ID
- **Line 8**: Establish Socket.IO connection to server
- **Line 11**: Emit 'join' event to server to join the room

### Lines 14-28: Set Up UI Event Listeners
```javascript
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
```
- **Line 14**: When send button clicked, call sendMessage()
- **Lines 15-20**: When Enter pressed (without Shift), send message
- **Lines 22-24**: When image button clicked, trigger hidden file input
- **Line 26**: When image selected, call handleImageUpload()
- **Line 27**: When leave room button clicked, call leaveRoom()
- **Line 28**: When back button clicked, call goBackToRooms()

### Lines 31-52: Set Up Socket Event Handlers
```javascript
    socket.on('new_message', function(data) {
        addMessageToUI(data);
        scrollToBottom();
    });
    
    socket.on('notification', function(data) {
        showNotification(data.message, data.type);
    });
    
    socket.on('error', function(data) {
        showNotification(data.message, 'error');
    });
    
    socket.on('user_list_update', function(data) {
        updateUserList(data.users, data.count);
    });
    
    scrollToBottom();
```
- **Lines 31-34**: When 'new_message' event received, add message to UI and scroll
- **Lines 36-38**: When 'notification' event received, show notification
- **Lines 41-43**: When 'error' event received, show error notification
- **Lines 46-48**: When 'user_list_update' received, update active users list
- **Line 51**: Scroll to bottom on initial load

### Lines 55-67: Send Message Function
```javascript
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
```
- **Line 56**: Get message input element
- **Line 57**: Get message text and trim whitespace
- **Line 59**: Check if message is not empty
- **Lines 60-64**: Emit 'message' event to server with room_id, content, and type
- **Line 65**: Clear input field

### Lines 69-85: Handle Image Upload Function
```javascript
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
    
    e.target.value = '';
}
```
- **Line 70**: Get selected file
- **Line 71**: If no file, exit
- **Line 73**: Create FileReader to read file as data URL
- **Lines 74-80**: When file loaded, emit 'image' event with base64 data
- **Line 81**: Read file as data URL (base64)
- **Line 84**: Clear file input

### Lines 87-121: Add Message to UI Function
```javascript
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
```
- **Line 88**: Get messages container element
- **Lines 90-91**: Create message div with 'message' class
- **Lines 93-94**: Create header div for username and timestamp
- **Lines 96-97**: Create strong element for username
- **Lines 99-101**: Create timestamp span with formatted time
- **Lines 103-104**: Add username and timestamp to header
- **Line 106**: Add header to message
- **Lines 108-118**: If text message, create paragraph; if image, create img element
- **Line 120**: Add complete message to container

### Lines 123-139: Show Notification Function
```javascript
function showNotification(message, type) {
    const notificationArea = document.getElementById('notification-area');
    
    const notification = document.createElement('div');
    notification.classList.add('notification', type);
    notification.textContent = message;
    
    notificationArea.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
    
    notificationArea.scrollTop = notificationArea.scrollHeight;
}
```
- **Line 124**: Get notification area element
- **Lines 126-128**: Create notification div with type class and message text
- **Line 130**: Add notification to area
- **Lines 133-135**: Remove notification after 5 seconds
- **Line 137**: Scroll notification area to bottom

### Lines 141-148: Leave and Navigation Functions
```javascript
function leaveRoom() {
    socket.emit('leave', { room_id: currentRoomId });
    goBackToRooms();
}

function goBackToRooms() {
    window.location.href = '/chat';
}
```
- **Lines 141-144**: Leave room by emitting 'leave' event and navigating away
- **Lines 146-148**: Navigate back to room list page

### Lines 150-153: Scroll Function
```javascript
function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
```
- Scroll messages container to bottom to show latest messages

### Lines 155-173: Update User List Function
```javascript
function updateUserList(users, count) {
    const activeCountEl = document.getElementById('active-count');
    if (activeCountEl) {
        activeCountEl.textContent = count;
    }
    
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
```
- **Lines 157-160**: Update active user count display
- **Lines 162-172**: Clear and rebuild user list with current active users
- **Line 169**: Create user item with bullet point indicator

---

## 5. static/style.css - Styling

### Lines 1-12: Global Styles
```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background-color: #f0f2f5; height: 100vh; }
```
- **Lines 2-6**: Reset default margins/padding, use border-box sizing
- **Lines 9-11**: Set body background and full viewport height

### Lines 14-53: Login Page Styles
```css
.login-container { /* styling */ }
```
- **Lines 15-23**: Center login container, white background, shadow
- **Lines 25-28**: Login heading styling
- **Lines 30-37**: Input field styling
- **Lines 39-53**: Button styling with hover effect

### Lines 55-124: Main Chat Layout
```css
.chat-container { display: flex; height: 100vh; }
.sidebar { width: 300px; background-color: #2c3e50; }
.main-content { flex: 1; display: flex; flex-direction: column; }
```
- **Lines 56-59**: Flexbox layout for sidebar and main content
- **Lines 61-68**: Dark sidebar (300px wide)
- **Lines 70-88**: User info section in sidebar
- **Lines 90-117**: Room list styling
- **Lines 119-124**: Main content area (takes remaining space)

### Lines 126-154: Welcome Message
```css
.welcome-message { /* centered card */ }
```
- Styled welcome card for main chat page before entering a room

### Lines 156-180: Room Header
```css
.chat-header { /* sticky header */ }
```
- White header with room name and leave button

### Lines 181-219: Chat Messages
```css
.chat-messages { flex: 1; overflow-y: auto; }
.message { background-color: white; border-radius: 8px; }
```
- **Lines 182-186**: Scrollable messages area
- **Lines 188-195**: Individual message card styling
- **Lines 197-212**: Message header and content styling
- **Lines 214-219**: Image message styling

### Lines 221-263: Message Input Area
```css
.message-input { /* bottom input */ }
```
- **Lines 222-225**: Input area styling
- **Lines 227-236**: Textarea styling
- **Lines 238-263**: Button styling for send and image buttons

### Lines 265-293: Notifications
```css
.notification-area { /* notification panel */ }
.notification { /* individual notification */ }
```
- **Lines 266-273**: Notification area in sidebar
- **Lines 275-293**: Notification styling with type-based colors (join=green, leave=red, message=blue)

### Lines 295-339: Active Users List
```css
.active-users { /* user list panel */ }
.user-item { /* individual user */ }
.user-dot { animation: pulse 2s infinite; }
```
- **Lines 296-307**: Active users section styling
- **Lines 309-323**: Individual user item styling
- **Lines 325-339**: Pulsing green dot animation for active users

---

## 6. templates/login.html - Login Page

### Lines 1-16: HTML Structure
```html
<!DOCTYPE html>
<html>
<head>
    <title>Chat Login</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="login-container">
        <h1>Welcome to Group Chat</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Enter your username" required>
            <button type="submit">Join Chat</button>
        </form>
    </div>
</body>
</html>
```
- **Line 5**: Link to stylesheet using Flask's url_for
- **Line 10**: POST form to submit username
- **Line 11**: Text input for username (required)
- **Line 12**: Submit button

---

## 7. templates/index.html - Main Chat Page

### Lines 1-8: Head Section
```html
<head>
    <title>Group Chat</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
    <script src="{{ url_for('static', filename='script.js') }}"></script>
</head>
```
- **Line 5**: Link stylesheet
- **Line 6**: Load Socket.IO library from CDN
- **Line 7**: Load custom JavaScript

### Lines 10-27: Sidebar
```html
<div class="sidebar">
    <div class="user-info">
        <h2>Welcome, {{ username }}!</h2>
        <button id="logout-btn">Logout</button>
    </div>
    
    <div class="room-list">
        <h3>Available Rooms</h3>
        <ul>
            {% for room in rooms %}
            <li>
                <a href="{{ url_for('room', room_id=room.id) }}">{{ room.name }}</a>
            </li>
            {% endfor %}
        </ul>
    </div>
</div>
```
- **Line 13**: Display logged-in username
- **Line 14**: Logout button
- **Lines 20-24**: Loop through rooms and create links

### Lines 29-41: Main Content
```html
<div class="main-content">
    <div class="welcome-message">
        <h1>Group Chat App</h1>
        <p>Select a room from the sidebar to start chatting!</p>
        <p>Features:</p>
        <ul>
            <li>Real-time messaging</li>
            <li>Group chat rooms</li>
            <li>Image sharing</li>
            <li>Message history</li>
        </ul>
    </div>
</div>
```
- Welcome message with app features

### Lines 44-52: JavaScript
```html
<script>
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('logout-btn').addEventListener('click', function() {
            fetch('/logout', { method: 'POST' })
                .then(() => window.location.href = '/login');
        });
    });
</script>
```
- **Note**: This code attempts to call a `/logout` route that is **not implemented** in app.py. This is a missing feature in the current implementation. The logout button will not work as-is.

---

## 8. templates/room.html - Chat Room Page

### Lines 1-8: Head Section
```html
<head>
    <title>{{ room.name }} - Group Chat</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
    <script src="{{ url_for('static', filename='script.js') }}"></script>
</head>
```
- Load required styles and scripts

### Lines 11-34: Sidebar with Room Info
```html
<div class="sidebar">
    <div class="user-info">
        <h2>{{ username }}</h2>
        <button id="back-btn">Back to Rooms</button>
    </div>
    
    <div class="room-info">
        <h3>Room: {{ room.name }}</h3>
        <p>Active now: <span id="active-count">1</span></p>
        
        <div class="active-users">
            <h4>Active Users:</h4>
            <div id="active-users-list">
                <div class="user-item">
                    <span class="user-dot">●</span> {{ username }}
                </div>
            </div>
        </div>
    </div>
    
    <div class="notification-area" id="notification-area">
        <!-- Notifications will appear here -->
    </div>
</div>
```
- Display current username and back button
- Show room info with active user count
- Display active users list
- Notification area for join/leave/message notifications

### Lines 36-57: Chat Messages Area
```html
<div class="main-content">
    <div class="chat-header">
        <h2>{{ room.name }}</h2>
        <button id="leave-room">Leave Room</button>
    </div>
    
    <div class="chat-messages" id="chat-messages">
        {% for message in messages %}
        <div class="message">
            <div class="message-header">
                <strong>{{ message.user.username }}</strong>
                <span>{{ message.timestamp.strftime('%H:%M') }}</span>
            </div>
            {% if message.content_type == 'text' %}
            <p>{{ message.content }}</p>
            {% else %}
            <img src="{{ message.content }}" alt="Shared image" class="chat-image">
            {% endif %}
        </div>
        {% endfor %}
    </div>
```
- Header with room name and leave button
- Loop through existing messages and display them
- Show text or image based on content_type

### Lines 59-67: Message Input
```html
    <div class="message-input">
        <textarea id="message-input" placeholder="Type your message..."></textarea>
        <div class="input-actions">
            <input type="file" id="image-input" accept="image/*" style="display: none;">
            <button id="image-btn">📷</button>
            <button id="send-btn">Send</button>
        </div>
    </div>
</div>
```
- Textarea for typing messages
- Hidden file input for images
- Camera button and send button

### Lines 70-78: Initialize Chat JavaScript
```html
<script>
    const roomId = {{ room.id }};
    const userId = {{ user_id }};
    const username = "{{ username }}";
    
    document.addEventListener('DOMContentLoaded', function() {
        initChat(roomId, userId, username);
    });
</script>
```
- Pass room ID, user ID, and username to JavaScript
- Initialize chat when page loads

---

## 9. requirements.txt - Python Dependencies

```
Flask==2.0.1              # Web framework
Flask-SocketIO==5.3.6     # WebSocket support for real-time features
Flask-SQLAlchemy==2.5.1   # Database ORM
psycopg2-binary==2.9.1    # PostgreSQL adapter (not used with SQLite)
python-dotenv==0.19.0     # Environment variable management
Pillow==10.3.0            # Image processing library
```

Each dependency serves a specific purpose in the application.

---

## 10. .env - Environment Configuration

```
DATABASE_URL=sqlite:///chat.db        # SQLite database file location
SECRET_KEY=your-secret-key-here...   # Secret key for session encryption
```

- **Line 2**: Database connection string (using SQLite for simplicity)
- **Line 5**: Secret key for Flask session management (should be changed in production)

---

## 11. START_CHAT_APP.bat - Windows Startup Script

This batch file provides a user-friendly way to start the application on Windows:

- **Lines 1-17**: Display information about the application
- **Line 19**: Change to script's directory
- **Line 20**: Run app.py with specific Python installation

---

## Application Flow

### 1. Starting the Application
1. Run `setup_db.py` to create database and initial rooms
2. Run `app.py` to start the server
3. Navigate to `http://127.0.0.1:5000`

### 2. User Journey
1. **Login**: Enter username → Creates/finds user in database → Redirected to chat page
2. **Room List**: View available rooms → Click room to enter
3. **Chat Room**: 
   - Join room (Socket.IO)
   - See active users
   - Send/receive messages in real-time
   - Share images
   - Leave room

### 3. Real-Time Communication
- Uses WebSocket via Socket.IO for bidirectional communication
- Server broadcasts messages to all users in same room
- Active user tracking updates in real-time
- Notifications for join/leave/message events

---

## Key Features

1. **User Authentication**: Simple username-based login
2. **Multiple Rooms**: Pre-configured chat rooms (General, Tech Talk, Random)
3. **Real-Time Messaging**: Instant message delivery using WebSockets
4. **Image Sharing**: Upload and share images (automatically resized)
5. **User Presence**: See who's currently active in each room
6. **Message History**: Last 20 messages loaded when entering room
7. **Notifications**: Real-time notifications for user actions

---

## Database Schema

```
User
├── id (PK)
├── username (unique)
└── relationships: messages, room_memberships

Room
├── id (PK)
├── name
└── relationships: messages, members

Message
├── id (PK)
├── content (text or base64 image)
├── content_type ('text' or 'image')
├── timestamp
├── user_id (FK → User)
└── room_id (FK → Room)

RoomMember
├── id (PK)
├── user_id (FK → User)
└── room_id (FK → Room)
```

---

## Technologies Used

- **Backend**: Python Flask
- **Real-Time**: Socket.IO (WebSockets)
- **Database**: SQLAlchemy ORM with SQLite
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Image Processing**: PIL (Pillow)

---

## Security Considerations

**Current Implementation (Development)**:
- Simple username authentication (no passwords)
- Secret key in .env file
- CORS enabled for all origins

**Production Recommendations**:
- Implement proper authentication (passwords, tokens)
- Use environment-specific secret keys
- Restrict CORS origins
- Add input validation and sanitization
- Implement rate limiting
- Use HTTPS

---

## Conclusion

This is a full-featured real-time chat application demonstrating:
- Flask web framework
- Socket.IO for real-time features
- SQLAlchemy ORM for database management
- Client-server WebSocket communication
- Image upload and processing
- User presence tracking

The code is well-structured, modular, and ready for educational purposes or further development into a production application.
