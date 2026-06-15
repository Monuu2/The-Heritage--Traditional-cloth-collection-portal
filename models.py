from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(200))

    phone = db.Column(db.String(15))

    profile_photo = db.Column(db.String(200))

    is_active = db.Column(db.Boolean, default=True)

    is_admin = db.Column(db.Boolean, default=False)

    failed_login_attempts = db.Column(db.Integer, default=0)

    locked_until = db.Column(db.DateTime, nullable=True)


    @property
    def is_locked(self):
        locked_until = getattr(self, 'locked_until', None)
        if locked_until and locked_until > datetime.utcnow():
            return True
        return False

    orders = db.relationship("Order", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False, unique=True)

    items = db.relationship("ClothItem", backref="category", lazy=True)


class ClothItem(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    name = db.Column(db.String(200), nullable=False)

    price = db.Column(db.Float, nullable=False)

    description = db.Column(db.Text)

    stock = db.Column(db.Integer, default=0)

    image_url = db.Column(db.String(200))

    daily_available = db.Column(db.Boolean, default=True)

    @property
    def average_rating(self):
        # Local import to avoid circular dependency
        from models import Review
        reviews = Review.query.filter_by(item_id=self.id).all()
        if not reviews:
            return 0.0
        
        valid_ratings = [r.rating for r in reviews if r.rating is not None]
        if not valid_ratings:
            return 0.0
            
        return round(sum(valid_ratings) / len(valid_ratings), 1)

    @property
    def review_count(self):
        from models import Review
        return Review.query.filter_by(item_id=self.id).count()


class Order(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey("cloth_item.id"), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=1)

    total_price = db.Column(db.Float, nullable=False, default=0)

    status = db.Column(db.String(50), nullable=False, default="Placed")

    created_at = db.Column(db.DateTime, default=db.func.now())

    # Stores delivery address as a JSON string
    delivery_address = db.Column(db.Text, nullable=True)

    item = db.relationship("ClothItem")


class Feedback(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey("cloth_item.id"), nullable=True)

    rating = db.Column(db.Integer)

    comment = db.Column(db.Text)

class Wishlist(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey("cloth_item.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=db.func.now())

    item = db.relationship("ClothItem")

    __table_args__ = (
        db.UniqueConstraint("user_id", "item_id", name="uq_wishlist_user_item"),
    )

class Review(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey("cloth_item.id"), nullable=False)

    rating = db.Column(db.Integer)

    comment = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=db.func.now())

class Cart(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey("cloth_item.id"), nullable=False)

    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("ClothItem")

class AdminUser(UserMixin):
    """Wraps a User for the admin_login_manager session."""
    def __init__(self, user):
        self.id            = user.id
        self.username      = user.username
        self.email         = user.email
        self.profile_photo = user.profile_photo
        self.is_admin      = user.is_admin
        self.is_active     = user.is_active

    def get_id(self):
        return str(self.id)
