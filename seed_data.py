from app import app
from models import db, Category, ClothItem, Order, Wishlist, Review, Cart, Feedback

with app.app_context():

    # Clear old data
    db.session.query(Order).delete()
    db.session.query(Wishlist).delete()
    db.session.query(Review).delete()
    db.session.query(Cart).delete()
    db.session.query(Feedback).delete()
    db.session.query(ClothItem).delete()
    db.session.query(Category).delete()

    # Categories
    categories = [
        "For Him",
        "For Her",
        "Jewellery",
        "Others"
    ]

    category_objects = {}

    for i, name in enumerate(categories):
        c = Category(id=i+1, name=name)
        db.session.add(c)
        db.session.flush()
        category_objects[name] = c.id

    products = [
        ("Traditional Bodo Gamsa", 800, "For Him", "gamsa_yellow_agor.jpg"),
        ("Men's Traditional Coat", 3500, "For Him", "https://www.mystore.in/s/62ea2c599d1398fa16dbae0a/66a7651598bfd3033f0d2dcc/1000053452-removebg-preview.png"),
        ("Traditional Black Handwoven Aronai", 1699, "For Him", "https://indigenousproducts.in/wp-content/uploads/2023/07/Bodo-Aronai-Black.jpg"),
        
        ("Authentic Bodo Dokhona", 4500, "For Her", "https://m.media-amazon.com/images/I/51xI2sn-85L._AC_UY1100_.jpg"),
        ("Traditional Fali (Scarf)", 600, "For Her", "https://images.unsplash.com/photo-1578932750294-f5075e85f44a"),
        ("Handwoven Dokhona Blouse", 1500, "For Her", "https://img.indiahandmade.com/catalog/product/cache/dee0bc41489afb86ae85561eae1bc64e/d/o/dokhona.jpg"),
        
        ("Traditional Aronai", 1200, "Others", "https://m.media-amazon.com/images/I/712RkIJv9qL._AC_UY1100_.jpg"),
        
        ("Traditional Gohena", 5000, "Jewellery", "https://m.media-amazon.com/images/I/61FMxU2N8EL._AC_UY1100_.jpg"),        
        ("Gold Plated Jewellery Set", 3000, "Jewellery", "https://jewelemarket.com/cdn/shop/files/11053097GL_63f6e48d-d2b1-4bc0-9e6f-494e7b1b18c2.jpg?v=1738994936"),
        ("Traditional Bead Necklace", 1800, "Jewellery", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQvtsluxG3j2ovU-QgyNIgOkPyD-qxdJhYmzA&s")
    ]

    for name, price, category, image in products:
        item = ClothItem(
            name=name,
            price=price,
            description="Premium handcrafted Bodo clothing and accessories.",
            stock=10,
            image_url=image,
            category_id=category_objects[category]
        )

        db.session.add(item)

    db.session.commit()

print("Database seeded successfully!")
