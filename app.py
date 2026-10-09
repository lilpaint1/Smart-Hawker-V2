"""Smart Hawker — Flask app (จุดเริ่มต้น)
รัน local:  python app.py   (หรือ flask run)
Production: gunicorn "app:app" --bind 0.0.0.0:$PORT --workers 3
"""
import os
import sys
import logging
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for, request
from werkzeug.middleware.proxy_fix import ProxyFix

# Windows console เป็น cp1252 พิมพ์ไทย/emoji ไม่ได้ -> บังคับ UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv()

from extensions import db
from constants import CLIENT_CONFIG, ROLE_LABEL, ACCENT_THEMES
from helpers import current_user
from api import api  # blueprint รวม API ทั้งหมด

logger = logging.getLogger(__name__)


def _auto_migrate(db):
    """Add new columns to existing SQLite DB (safe, idempotent).
    Each statement is tried independently — already-existing columns are silently skipped."""
    stmts = [
        "ALTER TABLE otp_code ADD COLUMN attempts INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE user ADD COLUMN verification_status TEXT DEFAULT 'UNVERIFIED' NOT NULL",
        "ALTER TABLE user ADD COLUMN id_hash TEXT",
        "ALTER TABLE user ADD COLUMN verified_name TEXT",
        "ALTER TABLE user ADD COLUMN verified_at DATETIME",
        "ALTER TABLE booking ADD COLUMN start_date DATETIME",
        "ALTER TABLE booking ADD COLUMN end_date DATETIME",
        "ALTER TABLE market ADD COLUMN cover_photo_url TEXT",
        "ALTER TABLE market ADD COLUMN is_featured INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE market ADD COLUMN is_verified INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE market ADD COLUMN owner_type TEXT DEFAULT 'PRIVATE' NOT NULL",
        "ALTER TABLE market ADD COLUMN gov_ref TEXT",
        "ALTER TABLE review ADD COLUMN is_hidden INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE notification ADD COLUMN link TEXT",
        "ALTER TABLE notification ADD COLUMN read INTEGER DEFAULT 0 NOT NULL",
    ]
    with db.engine.connect() as conn:
        for sql in stmts:
            try:
                conn.execute(db.text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists


def create_app():
    app = Flask(__name__)

    # ---- config ----
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    # DB path ต้อง "ตายตัว" ไม่ผูกกับ working directory ที่รัน — ไม่งั้นรันคนละโฟลเดอร์
    # จะเปิด dev.db คนละไฟล์ (DB ว่าง) ทำให้ล็อกอินไม่เจอ user (กันบั๊ก CWD-dependent DB)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    os.makedirs(os.path.join(base_dir, "instance"), exist_ok=True)
    default_db = "sqlite:///" + os.path.join(base_dir, "instance", "dev.db").replace("\\", "/")
    db_url = os.environ.get("DATABASE_URL", default_db)
    if db_url.startswith("postgres://"):          # Heroku/render compat
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"]        = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Secure cookie settings — SameSite+HttpOnly always; Secure only when env says so
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    if os.environ.get("SESSION_COOKIE_SECURE", "0") != "0":
        app.config["SESSION_COOKIE_SECURE"] = True

    # Max upload size (default 4 MB)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 4 * 1024 * 1024))

    # ProxyFix — real client IP when behind nginx/PythonAnywhere/Render
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    app.register_blueprint(api)

    with app.app_context():
        db.create_all()
        _auto_migrate(db)

    # ---- startup warnings ----
    if app.secret_key == "dev-secret-change-me-in-production":
        logger.warning("SECRET_KEY ยังใช้ค่า default — ห้ามใช้ใน production!")
    if not os.environ.get("ADMIN_CODE"):
        logger.warning("ADMIN_CODE ไม่ได้ตั้งค่า — admin login จะถูกปิดอัตโนมัติ!")
    if os.environ.get("SMS_PROVIDER", "console") == "console" and os.environ.get("FLASK_ENV") == "production":
        logger.warning("SMS_PROVIDER=console ใน production — OTP จะไม่ถูกส่งจริง!")
    if os.environ.get("IDENTITY_PROVIDER", "mock") == "mock" and os.environ.get("FLASK_ENV") == "production":
        logger.warning("IDENTITY_PROVIDER=mock ใน production — KYC จะไม่มีผล!")
    if os.environ.get("ENABLE_QUICK_LOGIN", "0") == "1" and os.environ.get("FLASK_ENV") == "production":
        logger.warning("ENABLE_QUICK_LOGIN=1 ใน production — ปิดใช้งานทันที!")

    # ---- security headers ----
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        if os.environ.get("SESSION_COOKIE_SECURE", "0") != "0":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    # ---- context processor ----
    @app.context_processor
    def inject_globals():
        me = current_user()
        return {
            "client_config":      CLIENT_CONFIG,
            "me":                 me,
            "session_role":       session.get("role"),
            "role_label":         ROLE_LABEL,
            "app_name":           os.environ.get("APP_NAME", "Smart Hawker"),
            "enable_quick_login": os.environ.get("ENABLE_QUICK_LOGIN", "1") != "0",
            "current_path":       request.path,
            "default_theme":      os.environ.get("DEFAULT_THEME", "light"),
            "default_lang":       os.environ.get("DEFAULT_LANG", "th"),
        }

    # ---- error handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Server error: %s", e)
        return render_template("errors/500.html"), 500

    register_pages(app)
    return app


# ----- page-level auth guards -----
def page_login_required(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        if not session.get("user_id"):
            return redirect(url_for("login_page", next=request.path))
        return fn(*a, **k)
    return wrapper


def page_admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        if session.get("role") != "ADMIN":
            return redirect(url_for("admin_login_page"))
        return fn(*a, **k)
    return wrapper


def register_pages(app):

    # ----- หน้าสาธารณะ (ไม่ต้อง login) -----
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        if session.get("user_id"):
            role = session.get("role")
            return redirect("/owner" if role == "MARKET_OWNER" else "/search")
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        return render_template("register.html")

    @app.route("/admin/login")
    def admin_login_page():
        if session.get("role") == "ADMIN":
            return redirect("/admin")
        return render_template("admin_login.html")

    # search และ market detail เป็น public (ดู brief §5.1)
    @app.route("/search")
    def search_page():
        return render_template("search.html")

    @app.route("/map")
    def map_page():
        return render_template("map.html")

    @app.route("/market/<mid>")
    def market_page(mid):
        return render_template("market.html", market_id=mid)

    # ----- หน้าที่ต้อง login -----
    @app.route("/book/<lot_id>")
    @page_login_required
    def book_page(lot_id):
        return render_template("book.html", lot_id=lot_id)

    @app.route("/checkout/<booking_id>")
    @page_login_required
    def checkout_page(booking_id):
        return render_template("checkout.html", booking_id=booking_id)

    @app.route("/confirm/<booking_id>")
    @page_login_required
    def confirm_page(booking_id):
        return render_template("confirm.html", booking_id=booking_id)

    @app.route("/confirm/<booking_id>/print")
    @page_login_required
    def confirm_print_page(booking_id):
        return render_template("confirm_print.html", booking_id=booking_id)

    @app.route("/bookings")
    @page_login_required
    def bookings_page():
        return render_template("bookings.html")

    @app.route("/chat")
    @page_login_required
    def chat_page():
        return render_template("chat.html")

    @app.route("/chat/<user_id>")
    @page_login_required
    def chat_thread_page(user_id):
        return render_template("chat_thread.html", other_id=user_id)

    @app.route("/profile")
    @page_login_required
    def profile_page():
        return render_template("profile.html")

    @app.route("/settings")
    @page_login_required
    def settings_page():
        return render_template("settings.html")

    @app.route("/notifications")
    @page_login_required
    def notifications_page():
        return render_template("notifications.html")

    @app.route("/favorites")
    @page_login_required
    def favorites_page():
        return render_template("favorites.html")

    @app.route("/owner")
    @page_login_required
    def owner_page():
        return render_template("owner.html")

    # ----- หน้าแอดมิน -----
    @app.route("/admin")
    @page_admin_required
    def admin_page():
        return render_template("admin.html")

    @app.route("/admin/users")
    @page_admin_required
    def admin_users_page():
        return render_template("admin_users.html")

    @app.route("/admin/markets")
    @page_admin_required
    def admin_markets_page():
        return render_template("admin_markets.html")

    @app.route("/admin/audit")
    @page_admin_required
    def admin_audit_page():
        return render_template("admin_audit.html")

    # ----- หน้าโปร่งใส (public) -----
    @app.route("/transparency")
    def transparency_page():
        return render_template("transparency.html")

    @app.route("/transparency/how-it-works")
    def transparency_how_page():
        return render_template("transparency_how.html")

    # ----- หน้าเจ้าหน้าที่ กทม. (read-only, public for demo) -----
    @app.route("/gov")
    def gov_page():
        return render_template("gov.html")

    # ----- Simulator (P2.1) -----
    @app.route("/simulator")
    def simulator_page():
        return render_template("simulator.html")


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
