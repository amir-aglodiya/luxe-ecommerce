import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Local development:
    #     instance/luxe.db
    #
    # Vercel:
    #     /tmp/luxe.db
    #
    # Vercel's deployment filesystem is read-only, while /tmp
    # is writable during the function runtime.
    if os.environ.get("VERCEL"):
        DATABASE = "/tmp/luxe.db"
    else:
        DATABASE = os.path.join(BASE_DIR, "instance", "luxe.db")
