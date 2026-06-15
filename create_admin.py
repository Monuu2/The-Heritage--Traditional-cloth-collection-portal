from app import app
from models import db, User

with app.app_context():
    admin = User.query.filter_by(email="admin@heritage.com").first()
    if not admin:
        admin = User(
            username="Admin",
            email="admin@heritage.com",
            phone="0000000000",
            is_admin=True
        )
        db.session.add(admin)
    else:
        admin.is_admin = True

    admin.set_password("admin123")
    db.session.commit()

    print("Admin account created successfully!")
    print("Email: admin@heritage.com | Password: admin123")
