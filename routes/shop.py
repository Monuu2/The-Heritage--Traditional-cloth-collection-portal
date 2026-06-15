from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import ClothItem, Category, Wishlist, Review, db

shop_bp = Blueprint("shop", __name__)

@shop_bp.route("/")
def index():
    featured_items = ClothItem.query.limit(4).all()
    return render_template("index.html", featured_items=featured_items)

@shop_bp.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    items = []
    if keyword:
        items = ClothItem.query.filter(ClothItem.name.ilike(f"%{keyword}%")).all()
    return render_template("products.html", items=items, search_query=keyword)

@shop_bp.route("/products")
def products():
    items = ClothItem.query.all()
    return render_template("products.html", items=items)

@shop_bp.route("/category/<int:category_id>")
def category_page(category_id):
    categories = Category.query.all()

    # Price filter parameters
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    if category_id == 0:
        query = ClothItem.query
        category_name = "All Products"
    else:
        category = Category.query.get(category_id)
        if category:
            query = ClothItem.query.filter_by(category_id=category_id)
            category_name = category.name
        else:
            query = ClothItem.query.filter(False)
            category_name = "Category"

    if min_price is not None:
        query = query.filter(ClothItem.price >= min_price)
    if max_price is not None:
        query = query.filter(ClothItem.price <= max_price)

    items = query.all()

    return render_template("category.html", items=items,
                           category_name=category_name,
                           categories=categories,
                           category_id=category_id,
                           min_price=min_price,
                           max_price=max_price)

@shop_bp.route("/item/<int:item_id>")
def item_detail(item_id):
    item = ClothItem.query.get_or_404(item_id)
    reviews = Review.query.filter_by(item_id=item_id).order_by(Review.created_at.desc()).all()
    return render_template("item.html", item=item, reviews=reviews)

@shop_bp.route("/review/<int:item_id>", methods=["POST"])
@login_required
def add_review(item_id):
    rating = request.form.get("rating", 5)
    comment = request.form.get("comment", "").strip()
    if comment:
        review = Review(user_id=current_user.id, item_id=item_id,
                        rating=int(rating), comment=comment)
        db.session.add(review)
        db.session.commit()
        flash("Review added successfully.")
    return redirect(url_for("shop.item_detail", item_id=item_id))

@shop_bp.route("/story")
def story():
    return render_template("story.html")
