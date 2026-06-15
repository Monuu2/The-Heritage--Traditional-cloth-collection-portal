from app import app
from models import db, Category

with app.app_context():

    Category.query.delete()

    db.session.commit()

    print("All categories deleted")

with app.app_context():

    db.session.add(Category(name="For Him"))
    db.session.add(Category(name="For Her"))
    db.session.add(Category(name="Jewellery"))
    db.session.add(Category(name="Others"))

    db.session.commit()

    print("Categories added")