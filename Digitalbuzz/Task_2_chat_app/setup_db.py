from models import db
from app import create_app

app = create_app()

with app.app_context():
    db.create_all()
    
    # Create some initial rooms
    from models import Room
    rooms = ['General', 'Tech Talk', 'Random']
    for room_name in rooms:
        if not Room.query.filter_by(name=room_name).first():
            new_room = Room(name=room_name)
            db.session.add(new_room)
    
    db.session.commit()
    print("Database setup complete!")