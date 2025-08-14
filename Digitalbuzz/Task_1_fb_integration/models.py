from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.String(100), primary_key=True)  # Facebook ID
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    
    pages = db.relationship('Page', backref='user', lazy=True)

class Page(db.Model):
    id = db.Column(db.String(100), primary_key=True)  # Page ID
    name = db.Column(db.String(100))
    access_token = db.Column(db.String(500))
    permissions = db.Column(db.String(500))  # Comma-separated permissions
    
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'))