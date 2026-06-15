from flask import Blueprint, session, redirect, url_for, render_template, flash, request
from models import db, ClothItem, Order
from flask_login import current_user, login_required
import json

order_bp = Blueprint("order", __name__)



@order_bp.route("/checkout", methods=["GET"])
@login_required
def checkout():
    """Show the delivery address form with optional last-used address."""
    last_order = Order.query.filter(Order.user_id == current_user.id, Order.delivery_address != None).order_by(Order.id.desc()).first()
    last_address = None
    if last_order and last_order.delivery_address:
        try:
            last_address = json.loads(last_order.delivery_address)
        except Exception:
            pass
    return render_template("user/delivery_add.html", last_address=last_address)


@order_bp.route("/checkout", methods=["POST"])
@login_required
def save_address():
    """Save delivery address to session and proceed to payment."""
    session['delivery_address'] = {
        'fullname': request.form.get('fullname', ''),
        'phone': request.form.get('phone', ''),
        'email': request.form.get('email', ''),
        'address_type': request.form.get('address_type', 'Home'),
        'line1': request.form.get('line1', ''),
        'line2': request.form.get('line2', ''),
        'landmark': request.form.get('landmark', ''),
        'city': request.form.get('city', ''),
        'state': request.form.get('state', ''),
        'pincode': request.form.get('pincode', ''),
        'country': request.form.get('country', 'India'),
    }
    session.modified = True
    return redirect(url_for('order.payment'))


@order_bp.route("/payment")
@login_required
def payment():
    """Show payment page with cart items."""
    cart = session.get("cart", [])
    items = []
    total = 0
    for item_id in cart:
        product = db.session.get(ClothItem, item_id)
        if product:
            items.append(product)
            total += product.price
    delivery = session.get('delivery_address', {})
    return render_template("payment.html", items=items, total=total, delivery=delivery)


@order_bp.route("/place-order")
@login_required
def place_order():
    cart = session.get("cart", [])
    if not cart:
        flash("Your cart is empty.")
        return redirect("/cart")
    delivery = session.get("delivery_address", {})
    delivery_json = json.dumps(delivery) if delivery else None
    for item_id in cart:
        product = db.session.get(ClothItem, item_id)
        if not product:
            continue
        if product.stock <= 0:
            flash(f"{product.name} is out of stock.")
            continue
        order = Order(
            user_id=current_user.id,
            item_id=product.id,
            quantity=1,
            total_price=product.price,
            status="Placed",
            delivery_address=delivery_json
        )
        product.stock -= 1
        db.session.add(order)
    db.session.commit()
    session["cart"] = []
    session.modified = True
    return redirect("/order-success")

@order_bp.route("/order-success")
@login_required
def order_success():
    return render_template("order_success.html")

@order_bp.route("/my-orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template("my_orders.html", orders=orders)

@order_bp.route("/cancel-order/<int:id>")
@login_required
def cancel_order(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        flash("You are not authorized to cancel this order.")
        return redirect("/my-orders")
    
    # We allow cancellation if it's placed, processing, etc (not delivered/shipped/cancelled)
    if order.status and order.status.lower() not in ['shipped', 'delivered', 'cancelled', 'returned']:
        order.status = "Cancelled"
        if order.item:
            order.item.stock += order.quantity or 1
        db.session.commit()
        flash(f"Order #{order.id} has been cancelled.")
    else:
        flash("This order cannot be cancelled anymore.")
        
    return redirect("/my-orders")

@order_bp.route("/return-order/<int:id>")
@login_required
def return_order(id):
    order = Order.query.get_or_404(id)
    if order.user_id != current_user.id:
        flash("You are not authorized to return this item.")
        return redirect("/my-orders")
        
    if order.status and order.status.lower() == 'delivered':
        order.status = "Returned"
        db.session.commit()
        flash(f"Return requested for order #{order.id}.")
    else:
        flash("Only delivered items can be returned.")
        
    return redirect("/my-orders")
