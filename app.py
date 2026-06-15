from flask import Flask, redirect, url_for
from config import Config
from models import db, User, Order
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)

# ── Security: CSRF Protection 
csrf = CSRFProtect(app)

# ── Security: Rate Limiting 
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ── Security: Secure Headers (Talisman) 
csp = {
    'default-src': "'self'",
    'script-src':  "'self' 'unsafe-inline'",
    'style-src':   "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
    'font-src':    "'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com",
    'img-src':     "'self' data: https:",
}
Talisman(app,
         force_https=False,                # Set True in production
         content_security_policy=csp,
         session_cookie_secure=False,      # Set True in production
)

# ── USER login manager 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None

# ── Image helper 
@app.template_global()
def img_src(image_url, default="default.png"):
    if not image_url:
        image_url = default
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    return url_for("static", filename="uploads/" + image_url)

# ── Jinja2 filter: parse JSON strings in templates
import json as _json
@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return _json.loads(value)
    except Exception:
        return {}

# ── Blueprints 
from routes.shop     import shop_bp
from routes.auth     import auth_bp
from routes.cart     import cart_bp
from routes.order    import order_bp
from routes.admin    import admin_bp
from routes.pages    import pages_bp
from routes.wishlist import wishlist_bp

app.register_blueprint(shop_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(order_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(wishlist_bp)

@app.route("/")
def home():
    return redirect(url_for("shop.index"))

@app.route('/buy/<int:product_id>')
@login_required
def buy(product_id):
    from models import ClothItem
    product = ClothItem.query.get_or_404(product_id)
    if product.stock <= 0:
        return redirect(url_for("shop.item_detail", item_id=product.id))
    order = Order(
        user_id=current_user.id,
        item_id=product.id,
        quantity=1,
        total_price=product.price,
        status="Placed"
    )
    product.stock -= 1
    db.session.add(order)
    db.session.commit()
    return redirect(url_for('order.my_orders'))

if __name__ == "__main__":
    app.run(debug=True)
