import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
from models import db, User, ClothItem, Order, Category
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from flask import session as flask_session
from models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def get_admin():
    """Returns the logged-in admin User or None."""
    admin_id = flask_session.get("_admin_user_id")
    if not admin_id:
        return None
    try:
        user = db.session.get(User, int(admin_id))
    except (TypeError, ValueError):
        return None
    if user and user.is_admin:
        return user
    return None

def admin_required():
    return get_admin() is not None

@admin_bp.route("/")
def admin_root():
    return redirect("/admin/dashboard")

@admin_bp.route("/dashboard")
def dashboard():
    if not admin_required():
        return redirect("/admin/login")
    users = User.query.count()
    products = ClothItem.query.count()
    orders = Order.query.count()
    total_earning = db.session.query(func.sum(Order.total_price)).scalar() or 0
    visitors = users * 3

    monthly_sales = [0] * 12
    monthly_revenue = [0] * 12
    all_orders = Order.query.all()
    for order in all_orders:
        if order.created_at:
            month = order.created_at.month - 1
        else:
            month = datetime.now().month - 1
        monthly_sales[month] += 1
        monthly_revenue[month] += order.total_price or 0

    top_products = db.session.query(
        ClothItem.id, ClothItem.name, ClothItem.image_url,
        func.sum(Order.quantity).label("qty")
    ).join(Order, ClothItem.id == Order.item_id)\
     .group_by(ClothItem.id, ClothItem.name, ClothItem.image_url)\
     .order_by(func.sum(Order.quantity).desc())\
     .limit(3).all()

    recent_orders = Order.query.order_by(Order.id.desc()).limit(5).all()

    return render_template("admin/dashboard.html",
        users=users, products=products, orders=orders,
        visitors=visitors, monthly_sales=monthly_sales,
        monthly_revenue=monthly_revenue, top_products=top_products,
        recent_orders=recent_orders, total_earning=total_earning, 
        admin=get_admin())

@admin_bp.route("/stock")
def stock():
    if not admin_required():
        return redirect("/admin/login")
    items = ClothItem.query.all()
    return render_template("admin/stock.html", items=items, admin=get_admin())

@admin_bp.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    if not admin_required():
        return redirect("/admin/login")
    item = ClothItem.query.get_or_404(id)
    categories = Category.query.all()
    if request.method == "POST":
        category_id = request.form.get("category", type=int)
        if not category_id or not Category.query.get(category_id):
            flash("Please select a valid category.")
            return render_template("admin/edit_product.html", item=item, categories=categories, admin=get_admin())
        item.name = request.form.get("name")
        item.price = float(request.form.get("price", 0))
        item.stock = int(request.form.get("stock", 0))
        item.category_id = category_id
        item.description = request.form.get("description")
        photo = request.files.get("image")
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            item.image_url = filename
        db.session.commit()
        flash("Product updated.")
        return redirect(url_for("admin.stock"))
    return render_template("admin/edit_product.html", item=item, categories=categories, admin=get_admin())

@admin_bp.route("/increase-stock/<int:id>")
def increase_stock(id):
    if not admin_required():
        return redirect("/admin/login")
    item = ClothItem.query.get_or_404(id)
    item.stock += 1
    db.session.commit()
    return redirect("/admin/stock")

@admin_bp.route("/decrease-stock/<int:id>")
def decrease_stock(id):
    if not admin_required():
        return redirect("/admin/login")
    item = ClothItem.query.get_or_404(id)
    if item.stock > 0:
        item.stock -= 1
    db.session.commit()
    return redirect("/admin/stock")

@admin_bp.route("/delete-stock/<int:id>")
def delete_stock(id):
    if not admin_required():
        return redirect("/admin/login")
    item = ClothItem.query.get_or_404(id)
    if Order.query.filter_by(item_id=item.id).first():
        flash("This product has orders and cannot be deleted. Set stock to 0 instead.")
        return redirect("/admin/stock")
    db.session.delete(item)
    db.session.commit()
    return redirect("/admin/stock")

@admin_bp.route("/add-product", methods=["GET", "POST"])
def add_product():
    if not admin_required():
        return redirect("/admin/login")
    categories = Category.query.all()
    if request.method == "POST":
        
        print("=== ADD PRODUCT DEBUG ===")
        print("FILES:", request.files)


        name = request.form.get("name")
        price = float(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
        category_id = request.form.get("category", type=int)
        description = request.form.get("description", "")
        image_url = "default.png"
        photo = request.files.get("image")

        print("PHOTO OBJECT:", photo)
        print("PHOTO FILENAME:", photo.filename if photo else "NO FILE")
        print("UPLOAD FOLDER:", current_app.config['UPLOAD_FOLDER'])


        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            image_url = filename
        if not category_id or not Category.query.get(category_id):
            flash("Please select a valid category.")
            return render_template("admin/add_product.html", categories=categories, admin=get_admin())
        product = ClothItem(name=name, price=price, stock=stock,
                            category_id=category_id, description=description,
                            image_url=image_url)
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully.")
        return redirect("/admin/stock")
    return render_template("admin/add_product.html", categories=categories, admin=get_admin())

@admin_bp.route("/users")
def users():
    if not admin_required():
        return redirect("/admin/login")
    users = User.query.all()
    return render_template("admin/users.html", users=users, admin=get_admin())

@admin_bp.route("/orders")
def orders():
    if not admin_required():
        return redirect("/admin/login")
    orders = Order.query.all()
    return render_template("admin/orders.html", orders=orders, admin=get_admin())

@admin_bp.route("/update-order/<int:id>/<status>")
def update_order(id, status):
    if not admin_required():
        return redirect("/admin/login")
    order = Order.query.get_or_404(id)
    order.status = status
    db.session.commit()
    return redirect("/admin/orders")
