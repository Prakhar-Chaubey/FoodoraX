from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask_mail import Mail, Message
from datetime import date, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash,send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
class HybridRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def hybrid_row_factory(cursor):
    columns = [col.name for col in cursor.description]

    def make_row(values):
        return HybridRow(zip(columns, values))

    return make_row

import os
import qrcode
import uuid

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get('FOODORAX_EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('FOODORAX_APP_PASSWORD')

app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('FOODORAX_EMAIL')

mail = Mail(app)

UPLOAD_FOLDER = os.path.join(
    app.root_path, "static", "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

app.secret_key = "FoodoraX-Hackathon-Secret-Key"

# SUPABASE / POSTGRESQL DATABASE CONNECTION

from dotenv import load_dotenv
load_dotenv(".env.local")

DATABASE_URL = os.environ.get("DATABASE_URL")



def get_db():
    conn = sqlite3.connect(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "foodorax.db"),
        timeout=30
    )
    conn.row_factory = sqlite3.Row
    return conn

# CREATE USER TABLE

def create_database():
    with get_db() as conn:
        cursor = conn.cursor()

        # Users Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                organization TEXT
            )
        """)

        # Food Donations Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER NOT NULL,
                food_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit TEXT NOT NULL,
                expiry TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (donor_id)
                REFERENCES users(id)
            )
        """)

        
        columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(donations)").fetchall()
        ]

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        if "pickup_instructions" not in columns:
            conn.execute("""
                ALTER TABLE donations
                ADD COLUMN pickup_instructions TEXT DEFAULT ''
            """)

        if "image" not in columns:
            conn.execute("""
                ALTER TABLE donations
                ADD COLUMN image TEXT DEFAULT NULL
            """)

        cursor.execute("PRAGMA table_info(donations)")
        columns = [column[1] for column in cursor.fetchall()]

        if "verification_id" not in columns:
            cursor.execute(
                "ALTER TABLE donations ADD COLUMN verification_id TEXT"
            )

        
        if "claimed_by" not in columns:
            conn.execute("""
                ALTER TABLE donations
                ADD COLUMN claimed_by INTEGER REFERENCES users(id)
            """)

        if "rejection_reason" not in columns:
            conn.execute("""
                ALTER TABLE donations
                ADD COLUMN rejection_reason TEXT DEFAULT ''
            """)

        if "reviewed_at" not in columns:
            conn.execute("""
                ALTER TABLE donations
                ADD COLUMN reviewed_at TIMESTAMP DEFAULT NULL
            """)

        conn.commit()

#ADMIN ACCOUNT      
def create_admin_account():
    import getpass

    print("\n--- FoodoraX Admin Setup ---")

    name = input("Admin Name: ").strip()
    email = input("Admin Email: ").strip().lower()
    password = getpass.getpass("Admin Password: ")

    if not name or not email or len(password) < 6:
        print("Invalid details. Password must be at least 6 characters.")
        return

    hashed_password = generate_password_hash(password)

    conn = get_db()

    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            print("This email is already registered.")
            return

        conn.execute("""
            INSERT INTO users
            (name, email, password, role, organization)
            VALUES (?, ?, ?, 'admin', 'FoodoraX Administration')
        """, (name, email, hashed_password))

        conn.commit()

        print("Admin account created successfully!")

    finally:
        conn.close()

# CURRENT USER
def get_current_user():
    user_id = session.get("user_id")

    if user_id:
        with get_db() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

    return None



def send_email_notification(recipient_email, subject, body):

    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>

        <body style="
            margin:0;
            padding:25px 10px;
            background-color:#F1F5F2;
            font-family:Arial,Helvetica,sans-serif;
            color:#1F2937;
        ">

            <div style="
                max-width:600px;
                margin:auto;
                background:#FFFFFF;
                border-radius:16px;
                overflow:hidden;
                border:1px solid #E5E7EB;
            ">

                <div style="
                    background:#0F5132;
                    padding:30px 20px;
                    text-align:center;
                ">
                    <h1 style="
                        color:#FFFFFF;
                        margin:0;
                        font-size:30px;
                    ">FoodoraX</h1>

                    <p style="
                        color:#D1FAE5;
                        margin:8px 0 0;
                        font-size:14px;
                    ">Turning Surplus into Smiles</p>
                </div>

                <div style="padding:30px 25px;">

                    <h2 style="
                        color:#0F5132;
                        margin-top:0;
                    ">Hello!</h2>

                    <p style="
                        font-size:15px;
                        line-height:1.8;
                        color:#374151;
                    ">{body.replace(chr(10), '<br>')}</p>

                    <div style="
                        background:#E8F5E9;
                        padding:18px;
                        border-radius:10px;
                        margin-top:25px;
                        text-align:center;
                    ">
                        <p style="
                            color:#0F5132;
                            font-weight:bold;
                            margin:0;
                        ">
                            Every meal shared is a smile created.
                        </p>
                    </div>

                </div>

                <div style="
                    background:#F9FAFB;
                    padding:20px;
                    text-align:center;
                    border-top:1px solid #E5E7EB;
                ">
                    <p style="
                        color:#6B7280;
                        font-size:12px;
                        margin:0;
                    ">
                        Thank you for being part of FoodoraX.
                    </p>

                    <p style="
                        color:#0F5132;
                        font-size:13px;
                        font-weight:bold;
                        margin:8px 0 0;
                    ">
                        FoodoraX Team
                    </p>
                </div>

            </div>

        </body>
        </html>
        """

        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body,
            html=html_body
        )

        mail.send(msg)

        print(f"Email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        print(f"Email sending failed: {e}")
        return False


@app.context_processor
def inject_notification_count():
    user = get_current_user()

    if not user:
        return {"unread_notifications": 0}

    with get_db() as conn:
        count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM notifications
            WHERE user_id = ? AND is_read = 0
        """, (user["id"],)).fetchone()["total"]

    return {"unread_notifications": count}



def create_notification(user_id, message):
    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO notifications (user_id, message)
            VALUES (?, ?)
        """, (user_id, message))

        conn.commit()

    finally:
        conn.close()


# HOME PAGE
@app.route("/")
def home():
    user = get_current_user()
    return render_template("index.html", user=user)


# REGISTER PAGE
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        organization = request.form.get("organization", "").strip()

        if not name or not email or not password:
            flash("Please fill all required fields.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must contain at least 6 characters.")
            return redirect(url_for("register"))

        if role not in ["donor", "recipient"]:
            flash("Please select a valid account type.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users
                    (name, email, password, role, organization)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name,
                    email,
                    hashed_password,
                    role,
                    organization
                ))

            # Send professional welcome email
            try:
                msg = Message(
                    subject="Welcome to FoodoraX | Turning Surplus into Smiles",
                    recipients=[email],
                    sender=app.config["MAIL_DEFAULT_SENDER"]
                )

                msg.body = f"""Dear {name},

Welcome to FoodoraX!

Thank you for joining our community and becoming part of a
mission that transforms surplus food into meaningful impact.

At FoodoraX, we aim to connect surplus food from donors with
people and communities who need it, helping reduce food waste
and create a more sustainable future.

Your account has been successfully created.

You can now explore FoodoraX and participate in our mission
to turn surplus into smiles.

Together, every contribution counts.

Thank you for being part of the change.

Warm regards,
Team FoodoraX
Turning Surplus into Smiles
"""

                mail.send(msg)
                print(f"Welcome email sent successfully to {email}")

            except Exception as e:
                print("Welcome email could not be sent:", e)

            flash("Account created successfully! Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This email is already registered.")
            return redirect(url_for("register"))

    return render_template("register.html")


# LOGIN PAGE
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]

            flash("Login successful!")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")



# DASHBOARD

@app.route("/dashboard")
def dashboard():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    today = date.today()
    tomorrow = today + timedelta(days=1)

    with get_db() as conn:

        # Automatically update expired available donations
        conn.execute("""
            UPDATE donations
            SET status = 'Expired'
            WHERE status = 'Available'
              AND expiry < ?
        """, (today.isoformat(),))

        if user["role"] == "donor":

            # Personal donor statistics
            total_listings = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE donor_id = ?
            """, (user["id"],)).fetchone()[0]

            available_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE donor_id = ?
                  AND status = 'Available'
            """, (user["id"],)).fetchone()[0]

            claimed_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE donor_id = ?
                  AND status IN ('Claimed', 'Completed')
            """, (user["id"],)).fetchone()[0]

            expired_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE donor_id = ?
                  AND status = 'Expired'
            """, (user["id"],)).fetchone()[0]

            expiring_soon = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE donor_id = ?
                  AND status = 'Available'
                  AND expiry BETWEEN ? AND ?
            """, (
                user["id"],
                today.isoformat(),
                tomorrow.isoformat()
            )).fetchone()[0]

            total_quantity = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM donations
                WHERE donor_id = ?
            """, (user["id"],)).fetchone()[0]

            # Donor's personal impact
            total_donations = total_listings

            successful_donations = claimed_food

            total_food_donated = total_quantity

            food_saved = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM donations
                WHERE donor_id = ?
                  AND status IN ('Claimed', 'Completed')
            """, (user["id"],)).fetchone()[0]

            # Only this donor's recent activity
            recent_donations = conn.execute("""
                SELECT
                    donations.id,
                    donations.food_name,
                    donations.quantity,
                    donations.unit,
                    donations.status,
                    donations.created_at,
                    users.name AS donor_name
                FROM donations
                JOIN users
                    ON donations.donor_id = users.id
                WHERE donations.donor_id = ?
                ORDER BY donations.id DESC
                LIMIT 5
            """, (user["id"],)).fetchall()

        elif user["role"] == "recipient":

            # Recipient's personal statistics
            total_listings = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE claimed_by = ?
            """, (user["id"],)).fetchone()[0]

            available_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status = 'Available'
            """).fetchone()[0]

            claimed_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE claimed_by = ?
                  AND status IN ('Claimed', 'Completed')
            """, (user["id"],)).fetchone()[0]

            expired_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE claimed_by = ?
                  AND status = 'Expired'
            """, (user["id"],)).fetchone()[0]

            expiring_soon = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status = 'Available'
                  AND expiry BETWEEN ? AND ?
            """, (
                today.isoformat(),
                tomorrow.isoformat()
            )).fetchone()[0]

            total_quantity = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM donations
                WHERE claimed_by = ?
                  AND status IN ('Claimed', 'Completed')
            """, (user["id"],)).fetchone()[0]

            total_donations = claimed_food
            successful_donations = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE claimed_by = ?
                  AND status = 'Completed'
            """, (user["id"],)).fetchone()[0]

            total_food_donated = total_quantity
            food_saved = total_quantity

            recent_donations = conn.execute("""
                SELECT
                    donations.id,
                    donations.food_name,
                    donations.quantity,
                    donations.unit,
                    donations.status,
                    donations.created_at,
                    users.name AS donor_name
                FROM donations
                JOIN users
                    ON donations.donor_id = users.id
                WHERE donations.claimed_by = ?
                ORDER BY donations.id DESC
                LIMIT 5
            """, (user["id"],)).fetchall()

        else:

            # Complete platform statistics for admin
            total_listings = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status = 'Available'
            """).fetchone()[0]

            available_food = total_listings

            claimed_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status IN ('Claimed', 'Completed')
            """).fetchone()[0]

            expired_food = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status = 'Expired'
            """).fetchone()[0]

            expiring_soon = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status = 'Available'
                  AND expiry BETWEEN ? AND ?
            """, (
                today.isoformat(),
                tomorrow.isoformat()
            )).fetchone()[0]

            total_quantity = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM donations
            """).fetchone()[0]

            total_donations = conn.execute("""
                SELECT COUNT(*)
                FROM donations
            """).fetchone()[0]

            successful_donations = conn.execute("""
                SELECT COUNT(*)
                FROM donations
                WHERE status IN ('Claimed', 'Completed')
            """).fetchone()[0]

            total_food_donated = total_quantity

            food_saved = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM donations
                WHERE status IN ('Claimed', 'Completed')
            """).fetchone()[0]

            recent_donations = conn.execute("""
                SELECT
                    donations.id,
                    donations.food_name,
                    donations.quantity,
                    donations.unit,
                    donations.status,
                    donations.created_at,
                    users.name AS donor_name
                FROM donations
                JOIN users
                    ON donations.donor_id = users.id
                ORDER BY donations.id DESC
                LIMIT 5
            """).fetchall()

        # Success rate for the current dashboard scope
        if total_donations > 0:
            donation_success_rate = round(
                (successful_donations / total_donations) * 100,
                1
            )
        else:
            donation_success_rate = 0

        # Community figures are global only for admin.
        # For donors and recipients, use personal figures.
        if user["role"] == "admin":

            total_community_donations = total_donations
            total_community_claimed = successful_donations

            community_quantity = food_saved

        else:

            total_community_donations = total_donations
            total_community_claimed = successful_donations
            community_quantity = food_saved

    return render_template(
        "dashboard.html",
        user=user,
        total_listings=total_listings,
        available_food=available_food,
        claimed_food=claimed_food,
        expired_food=expired_food,
        expiring_soon=expiring_soon,
        total_quantity=total_quantity,
        total_community_donations=total_community_donations,
        total_community_claimed=total_community_claimed,
        community_quantity=community_quantity,
        total_donations=total_donations,
        successful_donations=successful_donations,
        total_food_donated=total_food_donated,
        food_saved=food_saved,
        donation_success_rate=donation_success_rate,
        recent_donations=recent_donations
    )
    
#ADMIN
@app.route("/admin")
def admin_dashboard():
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "admin":
        flash("Access denied! Admin only.")
        return redirect(url_for("dashboard"))

    with get_db() as conn:

        # User Statistics
        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_donors = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'donor'"
        ).fetchone()[0]

        total_recipients = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'recipient'"
        ).fetchone()[0]

        # Donation Statistics
        total_donations = conn.execute(
            "SELECT COUNT(*) FROM donations"
        ).fetchone()[0]

        available_donations = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Available'"
        ).fetchone()[0]

        claimed_donations = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Claimed'"
        ).fetchone()[0]

        completed_donations = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Completed'"
        ).fetchone()[0]

        expired_donations = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Expired'"
        ).fetchone()[0]

        # Recent Users
        recent_users = conn.execute("""
            SELECT id, name, email, role, organization
            FROM users
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

        # Recent Donations
        recent_donations = conn.execute("""
            SELECT
                donations.id,
                donations.food_name,
                donations.quantity,
                donations.unit,
                donations.status,
                donations.created_at,
                users.name AS donor_name
            FROM donations
            JOIN users ON donations.donor_id = users.id
            ORDER BY donations.id DESC
            LIMIT 10
        """).fetchall()

    return render_template(
        "admin_dashboard.html",
        user=user,
        total_users=total_users,
        total_donors=total_donors,
        total_recipients=total_recipients,
        total_donations=total_donations,
        available_donations=available_donations,
        claimed_donations=claimed_donations,
        completed_donations=completed_donations,
        expired_donations=expired_donations,
        recent_users=recent_users,
        recent_donations=recent_donations
    )



@app.route("/admin/users")
def admin_users():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "admin":
        flash("Access denied! Admin only.")
        return redirect(url_for("dashboard"))

    with get_db() as conn:

        users = conn.execute("""
            SELECT id, name, email, role, organization
            FROM users
            ORDER BY id DESC
        """).fetchall()

        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_donors = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'donor'"
        ).fetchone()[0]

        total_recipients = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'recipient'"
        ).fetchone()[0]

    return render_template(
        "admin_users.html",
        user=user,
        users=users,
        total_users=total_users,
        total_donors=total_donors,
        total_recipients=total_recipients
    )


#ADMIN DONATIONS
@app.route("/admin/donations")
def admin_donations():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "admin":
        flash("Access denied! Admin only.")
        return redirect(url_for("dashboard"))

    with get_db() as conn:

        donations = conn.execute("""
            SELECT
                donations.id,
                donations.food_name,
                donations.category,
                donations.quantity,
                donations.unit,
                donations.expiry,
                donations.location,
                donations.status,
                donations.rejection_reason,
                donations.created_at,   
                donors.name AS donor_name,
                recipients.name AS recipient_name
            FROM donations
            JOIN users AS donors
                ON donations.donor_id = donors.id
            LEFT JOIN users AS recipients
                ON donations.claimed_by = recipients.id
            ORDER BY donations.id DESC
        """).fetchall()

        total_donations = conn.execute(
            "SELECT COUNT(*) FROM donations"
        ).fetchone()[0]

        available = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Available'"
        ).fetchone()[0]

        claimed = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Claimed'"
        ).fetchone()[0]

        completed = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Completed'"
        ).fetchone()[0]

        expired = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Expired'"
        ).fetchone()[0]

        pending = conn.execute(
            "SELECT COUNT(*) FROM donations WHERE status = 'Available'"
        ).fetchone()[0]

    return render_template(
        "admin_donations.html",
        user=user,
        donations=donations,
        total_donations=total_donations,
        available=available,
        claimed=claimed,
        completed=completed,
        expired=expired,
        pending=pending
    )


# FOOD DONATION


@app.route("/donate", methods=["GET", "POST"])
def donate():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "donor":
        flash("Only food donors can create food listings.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        food_name = request.form.get("food_name", "").strip()
        category = request.form.get("category", "")
        quantity = request.form.get("quantity", type=int)
        unit = request.form.get("unit", "")
        expiry = request.form.get("expiry", "")
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()

        image_file = request.files.get("food_image")
        image_filename = None

        if image_file and image_file.filename:

            if not allowed_file(image_file.filename):
                flash("Only JPG, JPEG, PNG and WEBP images are allowed.")
                return redirect(url_for("donate"))

            image_filename = secure_filename(image_file.filename)

            image_filename = f"{user['id']}_{image_filename}"

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_filename
            )

            image_file.save(image_path)

        if not all([
            food_name,
            category,
            quantity,
            unit,
            expiry,
            location
        ]) or quantity <= 0:

            flash("Please enter valid food details.")
            return redirect(url_for("donate"))

        with get_db() as conn:
            conn.execute("""
                INSERT INTO donations (
                    donor_id,
                    food_name,
                    category,
                    quantity,
                    unit,
                    expiry,
                    location,
                    description,
                    image,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user["id"],
                food_name,
                category,
                quantity,
                unit,
                expiry,
                location,
                description,
                image_filename,
                "Available"
            ))

        flash("Food donation added successfully! It is now available for recipients.")

        return redirect(url_for("dashboard"))

    return render_template("donate.html", user=user)


# FOOD LISTINGS 
@app.route("/food-listings")
def food_listings():

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    today = date.today()
    tomorrow = today + timedelta(days=1)

    with get_db() as conn:

        # Automatically update expired available donations
        conn.execute("""
            UPDATE donations
            SET status = 'Expired'
            WHERE status = 'Available'
              AND expiry < ?
        """, (today.isoformat(),))

        query = """
            SELECT donations.*, donor.name AS donor_name,
                   recipient.name AS recipient_name
            FROM donations
            JOIN users AS donor
                ON donations.donor_id = donor.id
            LEFT JOIN users AS recipient
                ON donations.claimed_by = recipient.id
            WHERE 1=1
        """

        params = []

        if user["role"] == "donor":

            query += " AND donations.donor_id = ?"
            params.append(user["id"])

        elif user["role"] == "admin":

            pass

        else:

            query += """
                AND (
                    donations.status IN (
                        'Available',
                        'Expired',
                        'Claimed',
                        'Completed'
                    )
                    AND (
                        donations.status IN ('Available', 'Expired')
                        OR donations.claimed_by = ?
                    )
                )
            """

            params.append(user["id"])

        if search:
            query += " AND donations.food_name LIKE ?"
            params.append(f"%{search}%")

        if category:
            query += " AND donations.category = ?"
            params.append(category)

        if location:
            query += " AND donations.location LIKE ?"
            params.append(f"%{location}%")

        query += " ORDER BY donations.created_at DESC"

        donations = conn.execute(query, params).fetchall()

        categories = conn.execute("""
            SELECT DISTINCT category
            FROM donations
            ORDER BY category
        """).fetchall()

    updated_donations = []

    for food in donations:

        food_data = dict(food)

        if food["status"] == "Completed":
            display_status = "Picked Up ✓"

        elif food["status"] == "Claimed":
            display_status = "Claimed"

        elif food["status"] == "Expired":
            display_status = "Expired"

        elif food["status"] == "Pending":
            display_status = "Pending Approval"

        elif food["status"] == "Rejected":
            display_status = "Rejected"

        else:

            try:
                expiry_date = date.fromisoformat(food["expiry"][:10])

                if expiry_date <= tomorrow:
                    display_status = "Expiring Soon"
                else:
                    display_status = "Available"

            except (ValueError, TypeError):
                display_status = "Invalid Expiry"

        food_data["display_status"] = display_status
        updated_donations.append(food_data)

    return render_template(
        "food_listings.html",
        donations=updated_donations,
        user=user,
        search=search,
        selected_category=category,
        location=location,
        categories=categories
    )

#CLAIM FOOD
@app.route("/claim/<int:donation_id>", methods=["POST"])
def claim_food(donation_id):
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "recipient":
        flash("Only recipients can claim food.", "error")
        return redirect(url_for("food_listings"))

    with get_db() as conn:
        donation = conn.execute("""
            SELECT
                donations.*,
                users.name AS donor_name,
                users.email AS donor_email
            FROM donations
            JOIN users ON donations.donor_id = users.id
            WHERE donations.id = ?
        """, (donation_id,)).fetchone()

        if not donation or donation["status"] != "Available":
            flash("This food is no longer available.", "error")
            return redirect(url_for("food_listings"))


        try:
            expiry_date = date.fromisoformat(
                donation["expiry"][:10]
            )
        except (ValueError, TypeError):
            flash("Invalid expiry date. Please contact the donor.", "error")
            return redirect(url_for("food_listings"))

        if expiry_date < date.today():
            conn.execute("""
                UPDATE donations
                SET status = 'Expired'
                WHERE id = ?
                  AND status = 'Available'
            """, (donation_id,))

            flash("Sorry, this food has expired and cannot be claimed.", "error")
            return redirect(url_for("food_listings"))

        conn.execute("""
            UPDATE donations
            SET status = 'Claimed',
                claimed_by = ?
            WHERE id = ?
              AND status = 'Available'
        """, (user["id"], donation_id))

    create_notification(
        donation["donor_id"],
        f"{user['name']} claimed your food listing: {donation['food_name']}."
    )

    create_notification(
    user["id"],
    f"Your claim for '{donation['food_name']}' was successful. Please check the pickup instructions."
    )


    # Email to Donor
    donor_email_body = f"""
Hello {donation['donor_name']},

Great news! Your food donation has been successfully claimed.

DONATION SUMMARY
------------------------------
Food Item: {donation['food_name']}
Quantity: {donation['quantity']} {donation['unit']}
Donation ID: FX-{donation['id']:05d}
Status: CLAIMED

CLAIM INFORMATION
------------------------------
Claimed By: {user['name']}

Your generous contribution is helping reduce food waste
and bringing smiles to people in need.

Thank you for being a FoodoraX community hero!

With gratitude,
FoodoraX Team
Turning Surplus into Smiles
"""

    send_email_notification(
        donation["donor_email"],
        "🎉 FoodoraX | Your Donation Made an Impact!",
        donor_email_body
    )


    # Professional Email to Recipient
    recipient_email_body = f"""
Hello {user['name']},

Congratulations! Your food claim has been confirmed successfully.

YOUR CLAIM DETAILS
------------------------------
Food Item: {donation['food_name']}
Quantity: {donation['quantity']} {donation['unit']}
Donation ID: FX-{donation['id']:05d}
Claim Status: CONFIRMED

DONOR INFORMATION
------------------------------
Donor Name: {donation['donor_name']}

WHAT'S NEXT?
------------------------------
Please log in to your FoodoraX account and check the
pickup instructions for your claimed food.

Please coordinate with the donor before collecting
the food.

Thank you for being part of our mission to reduce
food waste and support the community.

With gratitude,
FoodoraX Team
Turning Surplus into Smiles
"""

    send_email_notification(
        user["email"],
        "💚 FoodoraX | Your Food Claim is Confirmed!",
        recipient_email_body
    )

    flash("Food claimed successfully!", "success")
    return redirect(url_for("food_listings"))


@app.route("/delete-donation/<int:donation_id>", methods=["POST"])
def delete_donation(donation_id):
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "donor":
        flash("Only donors can delete food listings.", "error")
        return redirect(url_for("food_listings"))

    with get_db() as conn:
        donation = conn.execute("""
            SELECT *
            FROM donations
            WHERE id = ? AND donor_id = ?
        """, (donation_id, user["id"])).fetchone()

        if not donation:
            flash("Food listing not found or unauthorized.", "error")

        elif donation["status"] != "Available":
            flash("Claimed food cannot be deleted.", "error")

        else:
            conn.execute("""
                DELETE FROM donations
                WHERE id = ? AND donor_id = ?
            """, (donation_id, user["id"]))

            flash("Food donation deleted successfully!", "success")

    return redirect(url_for("food_listings"))

#UNCLAIM FOOD
@app.route("/unclaim/<int:donation_id>", methods=["POST"])
def unclaim_food(donation_id):

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "recipient":
        flash("Only recipients can unclaim food.", "error")
        return redirect(url_for("food_listings"))

    donor_id = None
    food_name = None
    unclaimed = False

    with get_db() as conn:

        donation = conn.execute("""
            SELECT *
            FROM donations
            WHERE id = ?
        """, (donation_id,)).fetchone()

        if not donation:
            flash("Food listing not found.", "error")

        elif (
            donation["status"] != "Claimed"
            or donation["claimed_by"] != user["id"]
        ):
            flash("You cannot unclaim this food.", "error")

        else:

            conn.execute("""
                UPDATE donations
                SET status = 'Available',
                    claimed_by = NULL
                WHERE id = ?
            """, (donation_id,))

            donor_id = donation["donor_id"]
            food_name = donation["food_name"]
            unclaimed = True

    # Database update connection closes before notification insert
    if unclaimed:

        create_notification(
            donor_id,
            f"{user['name']} unclaimed your food listing: {food_name}."
        )

        flash("Food unclaimed successfully!", "success")

    return redirect(url_for("food_listings"))


#HISTORY

@app.route("/history")
def donation_history():
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:
        if user["role"] == "donor":
            history = conn.execute("""
                SELECT
                    donations.*,
                    donor.name AS donor_name,
                    recipient.name AS recipient_name
                FROM donations
                JOIN users AS donor
                    ON donations.donor_id = donor.id
                LEFT JOIN users AS recipient
                    ON donations.claimed_by = recipient.id
                WHERE donations.donor_id = ?
                ORDER BY donations.created_at DESC
            """, (user["id"],)).fetchall()

        else:
            history = conn.execute("""
                SELECT
                    donations.*,
                    donor.name AS donor_name,
                    recipient.name AS recipient_name
                FROM donations
                JOIN users AS donor
                    ON donations.donor_id = donor.id
                LEFT JOIN users AS recipient
                    ON donations.claimed_by = recipient.id
                WHERE donations.claimed_by = ?
                ORDER BY donations.created_at DESC
            """, (user["id"],)).fetchall()

    return render_template(
        "history.html",
        user=user,
        history=history
    )


#CERTIFICATE

@app.route("/certificate/<int:donation_id>")
def download_certificate(donation_id):

    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] != "donor":
        return "Only donors can download donation certificates.", 403

    with get_db() as conn:
        donation = conn.execute("""
            SELECT
                donations.*,
                users.name AS donor_name
            FROM donations
            JOIN users ON donations.donor_id = users.id
            WHERE donations.id = ?
              AND donations.donor_id = ?
              AND donations.status = 'Claimed'
        """, (donation_id, user["id"])).fetchone()

    if not donation:
        return "Certificate is not available for this donation.", 404


    # Generate Unique Verification ID

    verification_id = donation["verification_id"] if "verification_id" in donation.keys() else None

    if not verification_id:
        verification_id = f"FX-{uuid.uuid4().hex[:10].upper()}"

        conn = get_db()

        conn.execute(
            "UPDATE donations SET verification_id = ? WHERE id = ?",
            (verification_id, donation_id)
        )

        conn.commit()
        conn.close()

    # Generate QR Code

    qr_data = (
        f"http://127.0.0.1:5000/verify/{verification_id}"
    )

    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Background
    pdf.setFillColorRGB(0.91, 0.96, 0.92)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    # Certificate border
    pdf.setStrokeColorRGB(0.06, 0.32, 0.20)
    pdf.setLineWidth(4)
    pdf.rect(35, 35, width - 70, height - 70)

    # Branding
    pdf.setFillColorRGB(0.06, 0.32, 0.20)
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawCentredString(width / 2, height - 110, "FoodoraX")

    pdf.setFont("Helvetica-Oblique", 12)
    pdf.drawCentredString(
        width / 2,
        height - 135,
        "Turning Surplus into Smiles"
    )

    # Certificate title
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(
        width / 2,
        height - 205,
        "CERTIFICATE OF IMPACT"
    )

    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(
        width / 2,
        height - 255,
        "This certificate is proudly presented to"
    )

    # Donor name
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(
        width / 2,
        height - 305,
        donation["donor_name"]
    )

    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(
        width / 2,
        height - 355,
        "For contributing towards food redistribution"
    )

    pdf.drawCentredString(
        width / 2,
        height - 380,
        "and helping reduce food waste."
    )

    # Donation details
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(
        width / 2,
        height - 445,
        "Donation Details"
    )

    pdf.setFont("Helvetica", 13)

    pdf.drawCentredString(
        width / 2,
        height - 480,
        f"Food Item: {donation['food_name']}"
    )

    pdf.drawCentredString(
        width / 2,
        height - 510,
        f"Quantity: {donation['quantity']} {donation['unit']}"
    )

    pdf.drawCentredString(
        width / 2,
        height - 540,
        f"Donation ID: FX-{donation['id']:05d}"
    )

    pdf.drawCentredString(
        width / 2,
        height - 570,
        f"Date: {donation['created_at']}"
    )

    # QR Code Generation
    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    print("DEBUG: QR image generated successfully")
    print("DEBUG: QR buffer size:", len(qr_buffer.getvalue()))


    # QR Code on Certificate
    qr_buffer.seek(0)

    from reportlab.lib.utils import ImageReader

    qr_image = ImageReader(qr_buffer)

    pdf.drawImage(
        qr_image,
        width / 2 - 45,
        155,
        width=90,
        height=90,
        preserveAspectRatio=True,
        mask='auto'
    )

    # Verification ID
    pdf.setFillColorRGB(0.06, 0.32, 0.20)
    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawCentredString(
        width / 2,
        140,
        f"Verification ID: {verification_id}"
    )

    # Footer
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(
        width / 2,
        110,
        "Thank you for making a difference!"
    )

    pdf.setFont("Helvetica-Oblique", 11)
    pdf.drawCentredString(
        width / 2,
        85,
        "Every meal shared is a smile created."
    )

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"FoodoraX_Certificate_{donation['id']}.pdf",
        mimetype="application/pdf"
    )



@app.route("/notifications")
def notifications():
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:
        user_notifications = conn.execute("""
            SELECT *
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user["id"],)).fetchall()

        conn.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = ?
        """, (user["id"],))

    return render_template(
        "notifications.html",
        user=user,
        notifications=user_notifications
    )

#PICKUP DETAILS
@app.route("/pickup/<int:donation_id>", methods=["GET", "POST"])
def pickup_details(donation_id):
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    with get_db() as conn:
        donation = conn.execute(
            "SELECT * FROM donations WHERE id = ?",
            (donation_id,)
        ).fetchone()

        if not donation:
            flash("Food listing not found.")
            return redirect(url_for("food_listings"))

        if user["role"] == "donor":

            if donation["donor_id"] != user["id"]:
                flash("You cannot edit this donation.")
                return redirect(url_for("food_listings"))

            if request.method == "POST":
                instructions = request.form.get(
                    "pickup_instructions", ""
                ).strip()

                conn.execute("""
                    UPDATE donations
                    SET pickup_instructions = ?
                    WHERE id = ? AND donor_id = ?
                """, (instructions, donation_id, user["id"]))

                if donation["claimed_by"]:
                    create_notification(
                        donation["claimed_by"],
                        f"Pickup instructions updated for {donation['food_name']}. Please check pickup details."
                    )

                flash("Pickup instructions saved successfully!")
                return redirect(url_for("food_listings"))

        elif user["role"] == "recipient":

            if donation["claimed_by"] != user["id"]:
                flash("Only the recipient who claimed this food can access pickup details.")
                return redirect(url_for("food_listings"))

            if request.method == "POST":

                action = request.form.get("action")

                if action == "complete":

                    if donation["status"] != "Claimed":
                        flash("This donation is not available for pickup completion.")
                        return redirect(url_for("pickup_details", donation_id=donation_id))

                    conn.execute("""
                        UPDATE donations
                        SET status = 'Completed'
                        WHERE id = ?
                        AND claimed_by = ?
                        AND status = 'Claimed'
                    """, (donation_id, user["id"]))

                    # Save donation status before creating notification
                    conn.commit()

                    # Notify donor after transaction is committed
                    create_notification(
                        donation["donor_id"],
                        f"Pickup completed successfully for {donation['food_name']}!"
                    )

                    flash("Pickup completed successfully! Thank you for helping reduce food waste.")
                    return redirect(url_for("food_listings"))

                flash("Invalid pickup action.")

        else:
            flash("You are not authorized to access pickup details.")
            return redirect(url_for("food_listings"))

        donation = conn.execute(
            "SELECT * FROM donations WHERE id = ?",
            (donation_id,)
        ).fetchone()

    return render_template(
        "pickup.html",
        user=user,
        donation=donation
    )

@app.route("/verify/<verification_id>")
def verify_certificate(verification_id):

    conn = get_db()

    certificate = conn.execute("""
        SELECT
            donations.*,
            users.name AS donor_name
        FROM donations
        JOIN users ON donations.donor_id = users.id
        WHERE donations.verification_id = ?
    """, (verification_id,)).fetchone()

    conn.close()

    if certificate and certificate["status"] == "Claimed":
        return render_template(
            "verify.html",
            certificate=certificate,
            verified=True
        )

    return render_template(
        "verify.html",
        certificate=None,
        verified=False
    )


# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)