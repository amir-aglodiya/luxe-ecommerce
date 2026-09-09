from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, get_db
from werkzeug.security import generate_password_hash

PRODUCTS = [
    ("Sculpted leather tote", "Bags", "A structured everyday carry in full-grain Italian leather.", 21080, "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=900&q=85", 1),
    ("Silk bias blouse", "Apparel", "Fluid silk with a relaxed drape and luminous finish.", 13940, "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=85", 1),
    ("Satin slingback", "Shoes", "A softly pointed silhouette finished with a considered heel.", 16660, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=85", 1),
    ("Brushed gold watch", "Jewelry", "A minimal timepiece with a warm brushed-metal bracelet.", 26350, "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=85", 0),
    ("Cashmere wrap", "Apparel", "An airy layer woven from exceptionally soft cashmere.", 18700, "https://images.unsplash.com/photo-1608234807905-4466023792f5?auto=format&fit=crop&w=900&q=85", 0),
    ("Pearl drop earrings", "Jewelry", "Freshwater pearls suspended from polished sterling silver.", 10030, "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=900&q=85", 0),
    ("Mini crescent shoulder bag", "Bags", "A compact curved silhouette for essentials, finished in supple leather.", 12750, "https://images.unsplash.com/photo-1594223274512-ad4803739b7c?auto=format&fit=crop&w=900&q=85", 0),
    ("Linen column dress", "Apparel", "A clean summer column cut from breathable washed linen.", 17850, "https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=900&q=85", 0),
    ("Soft square loafer", "Shoes", "An easy leather loafer with a softly squared toe and low profile.", 15300, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85", 0),
    ("Sculptural silver ring", "Jewelry", "A fluid sterling silver ring designed to stand alone or stack.", 7650, "https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=900&q=85", 0),
    ("Ribbed cotton tank", "Apparel", "A refined everyday base layer in soft, substantial cotton rib.", 5100, "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=900&q=85", 0),
    ("Woven leather belt", "Accessories", "A tactile woven belt with a quietly polished brass buckle.", 6800, "https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=900&q=85", 0),
    ("Pebbled crossbody bag", "Bags", "A hands-free daily companion with a softly structured profile.", 11050, "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&w=900&q=85", 0),
    ("Merino knit polo", "Apparel", "A fine merino polo with a relaxed collar and clean finish.", 14450, "https://images.unsplash.com/photo-1610652492500-ded49ceeb378?auto=format&fit=crop&w=900&q=85", 0),
    ("Canvas weekend bag", "Bags", "A roomy cotton-canvas carryall for short trips and long days.", 9350, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=85", 0),
    ("Pleated midi skirt", "Apparel", "A fluid pleated skirt designed to move with an easy rhythm.", 13175, "https://images.unsplash.com/photo-1583496661160-fb5886a13d27?auto=format&fit=crop&w=900&q=85", 0),
    ("Minimal leather sandal", "Shoes", "A pared-back sandal with a supportive footbed and fine straps.", 11900, "https://images.unsplash.com/photo-1562273138-f46be4ebdf33?auto=format&fit=crop&w=900&q=85", 0),
    ("Amber pendant necklace", "Jewelry", "A warm amber pendant on a delicate adjustable chain.", 8500, "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=900&q=85", 0),
    ("Oversized acetate frames", "Accessories", "Sculpted acetate sunglasses with softly rounded geometry.", 10200, "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=900&q=85", 1),
    ("Textured cotton overshirt", "Apparel", "A lightweight overshirt with tactile texture and useful pockets.", 15300, "https://images.unsplash.com/photo-1596755389378-c31d21fd1273?auto=format&fit=crop&w=900&q=85", 1),
]

app = create_app()
with app.app_context():
    db = get_db()
    db.execute(
        """
        INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'ADMIN')
        ON CONFLICT(email) DO UPDATE SET name = excluded.name, password = excluded.password, role = 'ADMIN'
        """,
        ("Luxe Admin", "admin@luxe.local", generate_password_hash("Admin123!")),
    )
    db.execute("DELETE FROM products")
    db.executemany("INSERT INTO products (name, category, description, price, image, featured) VALUES (?, ?, ?, ?, ?, ?)", PRODUCTS)
    db.commit()
    print(f"Seeded {len(PRODUCTS)} products into {app.config['DATABASE']}")
