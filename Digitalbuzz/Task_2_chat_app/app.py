import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, User, Room, Message, RoomMember
from dotenv import load_dotenv
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.getenv('SECRET_KEY')
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    db.init_app(app)
    return app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

# Track active users in each room
active_users = {}  # {room_id: {session_id: username}}

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

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

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    rooms = Room.query.all()
    return render_template('index.html', 
                           username=session['username'], 
                           rooms=rooms,
                           user_id=session['user_id'])

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

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        print(f"User {session['username']} connected")

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

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)