import os
from flask import Flask, redirect, request, jsonify, render_template, session
import requests
from dotenv import load_dotenv
from models import db, User, Page

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.getenv('SECRET_KEY')
    db.init_app(app)
    return app

app = create_app()

# Facebook API endpoints
FB_AUTH_URL = "https://www.facebook.com/v12.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v12.0/oauth/access_token"
FB_API_URL = "https://graph.facebook.com/v12.0"

@app.route('/')
def home():
    """Show login button"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Redirect to Facebook login"""
    return redirect(
        f"{FB_AUTH_URL}?"
        f"client_id={os.getenv('FB_APP_ID')}&"
        f"redirect_uri={os.getenv('FB_REDIRECT_URI')}&"
        "scope=public_profile,email,pages_show_list"
    )

@app.route('/callback')
def callback():
    """Handle Facebook callback"""
    # Get authorization code
    code = request.args.get('code')
    if not code:
        return "Error: Missing authorization code", 400
    
    # Exchange code for access token
    token_data = {
        'client_id': os.getenv('FB_APP_ID'),
        'client_secret': os.getenv('FB_APP_SECRET'),
        'redirect_uri': os.getenv('FB_REDIRECT_URI'),
        'code': code
    }
    
    token_res = requests.get(FB_TOKEN_URL, params=token_data)
    if token_res.status_code != 200:
        return "Error: Failed to get access token", 400
    
    access_token = token_res.json().get('access_token')
    
    # Get user profile
    profile_res = requests.get(
        f"{FB_API_URL}/me",
        params={
            'fields': 'id,name,email',
            'access_token': access_token
        }
    )
    if profile_res.status_code != 200:
        return "Error: Failed to get user profile", 400
    
    profile_data = profile_res.json()
    
    # Check if user exists in DB
    user = User.query.get(profile_data['id'])
    if not user:
        user = User(
            id=profile_data['id'],
            name=profile_data.get('name'),
            email=profile_data.get('email')
        )
        db.session.add(user)
    
    # Get user's pages
    pages_res = requests.get(
        f"{FB_API_URL}/me/accounts",
        params={'access_token': access_token}
    )
    pages_data = pages_res.json().get('data', [])
    
    # Process each page
    for page in pages_data:
        # Get page permissions
        perm_res = requests.get(
            f"{FB_API_URL}/{page['id']}/permissions",
            params={'access_token': access_token}
        )
        permissions = ",".join(
            p['permission'] 
            for p in perm_res.json().get('data', []) 
            if p['status'] == 'granted'
        )
        
        # Update or create page record
        existing_page = Page.query.get(page['id'])
        if existing_page:
            existing_page.access_token = page.get('access_token')
            existing_page.permissions = permissions
        else:
            new_page = Page(
                id=page['id'],
                name=page.get('name'),
                access_token=page.get('access_token'),
                permissions=permissions,
                user_id=user.id
            )
            db.session.add(new_page)
    
    db.session.commit()
    
    # Store user ID in session
    session['user_id'] = user.id
    return redirect('/pages')

@app.route('/pages')
def list_pages():
    """Show user's pages and tokens"""
    if 'user_id' not in session:
        return redirect('/')
    
    user = User.query.get(session['user_id'])
    pages = Page.query.filter_by(user_id=user.id).all()
    
    return render_template('pages.html', user=user, pages=pages)

@app.route('/api/pages')
def api_pages():
    """API endpoint for pages data (JSON)"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user = User.query.get(session['user_id'])
    pages = [
        {
            "id": page.id,
            "name": page.name,
            "access_token": page.access_token,
            "permissions": page.permissions.split(",")
        }
        for page in user.pages
    ]
    
    return jsonify({
        "user": {"id": user.id, "name": user.name},
        "pages": pages
    })

if __name__ == '__main__':
    app.run(debug=True)