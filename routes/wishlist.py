from flask import Blueprint, redirect, render_template
from flask_login import login_required, current_user
from models import db, Wishlist, ClothItem

wishlist_bp = Blueprint("wishlist", __name__)

@wishlist_bp.route("/wishlist")
@login_required
def wishlist():

    items = Wishlist.query.filter_by(user_id=current_user.id).all()

    return render_template("wishlist.html", items=items)


@wishlist_bp.route("/wishlist/add/<int:item_id>")
@login_required
def add_wishlist(item_id):
    if not db.session.get(ClothItem, item_id):
        return redirect("/wishlist")
    if Wishlist.query.filter_by(user_id=current_user.id, item_id=item_id).first():
        return redirect("/wishlist")

    wish = Wishlist(user_id=current_user.id, item_id=item_id)

    db.session.add(wish)
    db.session.commit()

    return redirect("/wishlist")


@wishlist_bp.route("/wishlist/remove/<int:id>")
@login_required
def remove_wishlist(id):

    wish = db.session.get(Wishlist, id)
    if not wish or wish.user_id != current_user.id:
        return redirect("/wishlist")

    db.session.delete(wish)
    db.session.commit()

    return redirect("/wishlist")
