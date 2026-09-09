# Luxe Studio

A full-stack e-commerce starter built with Python, Flask, SQLite, Jinja templates, and vanilla CSS.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/seed_database.py
python3 run.py
```

Open `http://127.0.0.1:5000`.

## Included

- Responsive storefront homepage and catalog
- Category filtering and product detail pages
- Session-based shopping bag
- Account registration, sign in, and sign out
- Editable profile with name, phone, and delivery address
- Authenticated checkout that creates confirmed orders and saves order details in SQLite
- Protected database viewer at `/database` for users, products, orders, and order items
- Seed script with twenty example products and individual product photos
- Separate customer and admin roles with protected admin routes
- Admin dashboard, product creation/removal, order status updates, and customer order history

## Admin demo

Run the seed script, then open `/admin/login`:

- Email: `admin@luxe.local`
- Password: `Admin123!`

The SQLite database is created at `instance/luxe.db` on first run. Set `SECRET_KEY` in the environment before deploying.
