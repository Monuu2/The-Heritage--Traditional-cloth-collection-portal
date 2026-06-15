from app import app
from models import db, User

with app.app_context():
    admin = User.query.filter_by(email="admin@heritage.com").first()
    admin.is_active = True
    admin.is_admin = True
    db.session.commit()
    print("Admin updated successfully!")