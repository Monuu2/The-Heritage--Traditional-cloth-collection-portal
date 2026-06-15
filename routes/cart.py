from flask import Blueprint, session, redirect, url_for, render_template
from flask_login import login_required
from models import db, ClothItem

cart_bp = Blueprint("cart", __name__)

# View cart
@cart_bp.route("/cart")
@login_required
def view_cart():

    cart = session.get("cart", [])

    items = []
    total = 0

    for item_id in cart:

        product = db.session.get(ClothItem, item_id)

        if product:
            items.append(product)
            total += product.price

    return render_template("cart.html", items=items, total=total)


# Add item to cart
@cart_bp.route("/add-to-cart/<int:item_id>")
@login_required
def add_to_cart(item_id):
    product = db.session.get(ClothItem, item_id)
    if not product or product.stock <= 0:
        return redirect(url_for("cart.view_cart"))

    cart = session.get("cart", [])

    cart.append(item_id)

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart.view_cart"))


# Remove item from cart
@cart_bp.route("/remove-from-cart/<int:item_id>")
@login_required
def remove_from_cart(item_id):

    cart = session.get("cart", [])

    if item_id in cart:
        cart.remove(item_id)

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart.view_cart"))


@cart_bp.app_context_processor
def cart_count():

    cart = session.get("cart", [])

    return dict(cart_count=len(cart))
