from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
import os
from dotenv import load_dotenv
load_dotenv()
# ── App setup ──────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(BASE_DIR, "templates")
static_dir = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir
)

app.secret_key = os.environ["SECRET_KEY"]


print("Template folder:", template_dir)
print("Static folder:", static_dir)
print("Templates exist:", os.path.exists(template_dir))
print(
    "login.html exists:",
    os.path.exists(os.path.join(template_dir, "login.html"))
)


# ── Database ───────────────────────────────────────────────

try:
    db = mysql.connector.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ["DB_PASSWORD"],
    database=os.environ.get("DB_NAME", "airport_management")
)

    db.autocommit = True
    print("✅ Database connected successfully!")

except Exception as e:
    print(f"❌ Database connection failed: {e}")
    db = None


# ── Helper functions ───────────────────────────────────────

def admin_required():
    """
    Check whether the currently logged-in user is an admin.
    """

    if "user_id" not in session:
        return False

    role = session.get("role", "")
    return role.lower() == "admin"


def passenger_required():
    """
    Check whether the currently logged-in user is a passenger.
    """

    if "user_id" not in session:
        return False

    role = session.get("role", "")
    return role.lower() == "passenger"


# ── Default admin ──────────────────────────────────────────

def create_default_admin():

    if db is None:
        print("❌ Cannot create default admin because database is not connected.")
        return

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        # Check whether an admin already exists
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            ("admin@airport.com",)
        )

        admin = cursor.fetchone()

        if not admin:

            hashed_password = generate_password_hash("admin123")

            cursor.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    "Airport Admin",
                    "admin@airport.com",
                    hashed_password,
                    "Admin"
                )
            )

            db.commit()

            print("✅ Default admin account created.")
            print("   Email: admin@airport.com")
            print("   Password: admin123")

        else:
            print("ℹ️ Admin account already exists.")

    except Exception as e:

        if db:
            db.rollback()

        print("❌ Admin creation error:", e)

    finally:

        if cursor:
            cursor.close()


# ── Home ───────────────────────────────────────────────────

@app.route("/")
def home():
    return redirect(url_for("login"))


# ── Login ──────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            return render_template(
                "login.html",
                error="Please enter email and password."
            )

        cursor = None

        try:

            cursor = db.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT user_id, name, email, password, role
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                session["role"] = user["role"]

                if user["role"].lower() == "admin":
                    return redirect(url_for("admin_dashboard"))

                else:
                    return redirect(url_for("passenger_dashboard"))

            else:

                return render_template(
                    "login.html",
                    error="Invalid email or password."
                )

        except Exception as e:

            print("Login error:", e)

            return render_template(
                "login.html",
                error=f"Error: {str(e)}"
            )

        finally:

            if cursor:
                cursor.close()

    try:

        rendered = render_template("login.html")

        print(
            f"✅ login.html rendered successfully, length: {len(rendered)}"
        )

        return rendered

    except Exception as e:

        print("❌ Template render error:", e)

        return f"Template render error: {str(e)}", 500


# ── Register ────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Get form data
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        passport_no = request.form.get("passport_no", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate required fields
        if not all([
            name,
            email,
            phone,
            gender,
            date_of_birth,
            passport_no,
            password,
            confirm_password
        ]):

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        # Check passwords match
        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        # Hash password
        hashed_password = generate_password_hash(password)

        cursor = None

        try:

            cursor = db.cursor()

            # Check email
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                return render_template(
                    "register.html",
                    error="Email already registered. Please login."
                )

            # Check passport
            cursor.execute(
                """
                SELECT passenger_id
                FROM passengers
                WHERE passport_no = %s
                """,
                (passport_no,)
            )

            existing_passport = cursor.fetchone()

            if existing_passport:

                return render_template(
                    "register.html",
                    error="Passport number already registered."
                )

            # Insert user
            cursor.execute(
                """
                INSERT INTO users
                (name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    hashed_password,
                    "Passenger"
                )
            )

            user_id = cursor.lastrowid

            # Insert passenger
            cursor.execute(
                """
                INSERT INTO passengers
                (
                    user_id,
                    phone,
                    gender,
                    date_of_birth,
                    passport_no
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    phone,
                    gender,
                    date_of_birth,
                    passport_no
                )
            )

            db.commit()

            return render_template(
                "login.html",
                success="Account created successfully! Please login."
            )

        except Exception as e:

            db.rollback()

            print("Registration error:", e)

            return render_template(
                "register.html",
                error=f"Registration failed: {str(e)}"
            )

        finally:

            if cursor:
                cursor.close()

    return render_template("register.html")


# ══════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════

@app.route("/admin_dashboard")
def admin_dashboard():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        # Total passengers
        cursor.execute(
            "SELECT COUNT(*) AS total FROM passengers"
        )

        total_passengers = cursor.fetchone()["total"]

        # Total flights
        cursor.execute(
            "SELECT COUNT(*) AS total FROM flights"
        )

        total_flights = cursor.fetchone()["total"]

        # Total bookings
        cursor.execute(
            "SELECT COUNT(*) AS total FROM bookings"
        )

        total_bookings = cursor.fetchone()["total"]

        # Total airlines
        cursor.execute(
            "SELECT COUNT(*) AS total FROM airlines"
        )

        total_airlines = cursor.fetchone()["total"]

        # Total gates
        cursor.execute(
            "SELECT COUNT(*) AS total FROM gates"
        )

        total_gates = cursor.fetchone()["total"]

        # Total employees
        cursor.execute(
            "SELECT COUNT(*) AS total FROM employees"
        )

        total_employees = cursor.fetchone()["total"]

        # Confirmed bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE booking_status = 'Confirmed'
            """
        )

        confirmed_bookings = cursor.fetchone()["total"]

        # Cancelled bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE booking_status = 'Cancelled'
            """
        )

        cancelled_bookings = cursor.fetchone()["total"]

        # Revenue
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM bookings
            WHERE booking_status = 'Confirmed'
            """
        )

        total_revenue = cursor.fetchone()["total"]

        return render_template(
            "admin_dashboard.html",
            total_passengers=total_passengers,
            total_flights=total_flights,
            total_bookings=total_bookings,
            total_airlines=total_airlines,
            total_gates=total_gates,
            total_employees=total_employees,
            confirmed_bookings=confirmed_bookings,
            cancelled_bookings=cancelled_bookings,
            total_revenue=total_revenue
        )

    except Exception as e:

        print("Admin dashboard error:", e)

        return render_template(
            "admin_dashboard.html",
            error=f"Unable to load dashboard statistics: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# ADMIN: FLIGHTS
# ══════════════════════════════════════════════════════════

@app.route("/admin/flights")
def admin_flights():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                f.*,
                a.airline_name,
                a.airline_code,
                g.gate_number,
                g.terminal
            FROM flights f
            JOIN airlines a
                ON f.airline_id = a.airline_id
            LEFT JOIN gates g
                ON f.gate_id = g.gate_id
            ORDER BY f.departure_time DESC
            """
        )

        flights = cursor.fetchall()

    except Exception as e:

        flights = []

        print("Admin flights error:", e)

    finally:

        if cursor:
            cursor.close()

    return render_template(
        "admin_flights.html",
        flights=flights,
        error=request.args.get("error")
    )


@app.route("/admin/flights/add", methods=["GET", "POST"])
def admin_add_flight():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT airline_id, airline_name, airline_code
            FROM airlines
            ORDER BY airline_name
            """
        )

        airlines = cursor.fetchall()

        cursor.execute(
            """
            SELECT gate_id, gate_number, terminal
            FROM gates
            ORDER BY gate_number
            """
        )

        gates = cursor.fetchall()

        if request.method == "POST":

            flight_number = request.form.get(
                "flight_number", ""
            ).strip()

            airline_id = request.form.get("airline_id")

            source = request.form.get(
                "source", ""
            ).strip()

            destination = request.form.get(
                "destination", ""
            ).strip()

            departure_time = request.form.get(
                "departure_time"
            )

            arrival_time = request.form.get(
                "arrival_time"
            )

            gate_id = request.form.get("gate_id") or None

            status = request.form.get(
                "status", "Scheduled"
            )

            total_seats = request.form.get(
                "total_seats"
            )

            if not all([
                flight_number,
                airline_id,
                source,
                destination,
                departure_time,
                arrival_time,
                total_seats
            ]):

                return render_template(
                    "admin_flight_form.html",
                    airlines=airlines,
                    gates=gates,
                    flight=None,
                    error="Please fill in all required fields."
                )

            cursor.execute(
                """
                INSERT INTO flights
                (
                    flight_number,
                    airline_id,
                    source,
                    destination,
                    departure_time,
                    arrival_time,
                    gate_id,
                    status,
                    total_seats,
                    available_seats
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    flight_number,
                    airline_id,
                    source,
                    destination,
                    departure_time,
                    arrival_time,
                    gate_id,
                    status,
                    total_seats,
                    total_seats
                )
            )

            db.commit()

            return redirect(url_for("admin_flights"))

        return render_template(
            "admin_flight_form.html",
            airlines=airlines,
            gates=gates,
            flight=None
        )

    except Exception as e:

        db.rollback()

        print("Add flight error:", e)

        return render_template(
            "admin_flight_form.html",
            airlines=airlines if "airlines" in locals() else [],
            gates=gates if "gates" in locals() else [],
            flight=None,
            error=f"Failed to add flight: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


@app.route(
    "/admin/flights/edit/<int:flight_id>",
    methods=["GET", "POST"]
)
def admin_edit_flight(flight_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT airline_id, airline_name, airline_code
            FROM airlines
            ORDER BY airline_name
            """
        )

        airlines = cursor.fetchall()

        cursor.execute(
            """
            SELECT gate_id, gate_number, terminal
            FROM gates
            ORDER BY gate_number
            """
        )

        gates = cursor.fetchall()

        if request.method == "POST":

            flight_number = request.form.get(
                "flight_number", ""
            ).strip()

            airline_id = request.form.get("airline_id")

            source = request.form.get(
                "source", ""
            ).strip()

            destination = request.form.get(
                "destination", ""
            ).strip()

            departure_time = request.form.get(
                "departure_time"
            )

            arrival_time = request.form.get(
                "arrival_time"
            )

            gate_id = request.form.get("gate_id") or None

            status = request.form.get(
                "status", "Scheduled"
            )

            total_seats = request.form.get(
                "total_seats"
            )

            available_seats = request.form.get(
                "available_seats"
            )

            if not all([
                flight_number,
                airline_id,
                source,
                destination,
                departure_time,
                arrival_time,
                total_seats,
                available_seats
            ]):

                return render_template(
                    "admin_flight_form.html",
                    airlines=airlines,
                    gates=gates,
                    flight=None,
                    error="Please fill in all required fields."
                )

            cursor.execute(
                """
                UPDATE flights
                SET
                    flight_number = %s,
                    airline_id = %s,
                    source = %s,
                    destination = %s,
                    departure_time = %s,
                    arrival_time = %s,
                    gate_id = %s,
                    status = %s,
                    total_seats = %s,
                    available_seats = %s
                WHERE flight_id = %s
                """,
                (
                    flight_number,
                    airline_id,
                    source,
                    destination,
                    departure_time,
                    arrival_time,
                    gate_id,
                    status,
                    total_seats,
                    available_seats,
                    flight_id
                )
            )

            db.commit()

            return redirect(url_for("admin_flights"))

        cursor.execute(
            """
            SELECT *
            FROM flights
            WHERE flight_id = %s
            """,
            (flight_id,)
        )

        flight = cursor.fetchone()

        if not flight:
            return redirect(url_for("admin_flights"))

        return render_template(
            "admin_flight_form.html",
            airlines=airlines,
            gates=gates,
            flight=flight
        )

    except Exception as e:

        db.rollback()

        print("Edit flight error:", e)

        return render_template(
            "admin_flight_form.html",
            airlines=airlines if "airlines" in locals() else [],
            gates=gates if "gates" in locals() else [],
            flight=None,
            error=f"Failed to update flight: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


@app.route(
    "/admin/flights/delete/<int:flight_id>",
    methods=["POST"]
)
def admin_delete_flight(flight_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM flights
            WHERE flight_id = %s
            """,
            (flight_id,)
        )

        db.commit()

        return redirect(url_for("admin_flights"))

    except Exception as e:

        db.rollback()

        print("Delete flight error:", e)

        return redirect(
            url_for(
                "admin_flights",
                error="Cannot delete this flight — it has existing bookings."
            )
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# ADMIN: AIRLINES
# ══════════════════════════════════════════════════════════

@app.route("/admin/airlines")
def admin_airlines():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM airlines
            ORDER BY airline_name
            """
        )

        airlines = cursor.fetchall()

    except Exception as e:

        airlines = []

        print("Admin airlines error:", e)

    finally:

        if cursor:
            cursor.close()

    return render_template(
        "admin_airlines.html",
        airlines=airlines,
        error=request.args.get("error")
    )


@app.route(
    "/admin/airlines/add",
    methods=["GET", "POST"]
)
def admin_add_airline():

    if not admin_required():
        return redirect(url_for("login"))

    if request.method == "POST":

        airline_name = request.form.get(
            "airline_name", ""
        ).strip()

        airline_code = request.form.get(
            "airline_code", ""
        ).strip()

        country = request.form.get(
            "country", ""
        ).strip()

        if not all([
            airline_name,
            airline_code,
            country
        ]):

            return render_template(
                "admin_airline_form.html",
                airline=None,
                error="Please fill in all fields."
            )

        cursor = None

        try:

            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO airlines
                (
                    airline_name,
                    airline_code,
                    country
                )
                VALUES (%s, %s, %s)
                """,
                (
                    airline_name,
                    airline_code,
                    country
                )
            )

            db.commit()

            return redirect(url_for("admin_airlines"))

        except Exception as e:

            db.rollback()

            return render_template(
                "admin_airline_form.html",
                airline=None,
                error=f"Failed to add airline: {str(e)}"
            )

        finally:

            if cursor:
                cursor.close()

    return render_template(
        "admin_airline_form.html",
        airline=None
    )


@app.route(
    "/admin/airlines/edit/<int:airline_id>",
    methods=["GET", "POST"]
)
def admin_edit_airline(airline_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        if request.method == "POST":

            airline_name = request.form.get(
                "airline_name", ""
            ).strip()

            airline_code = request.form.get(
                "airline_code", ""
            ).strip()

            country = request.form.get(
                "country", ""
            ).strip()

            cursor.execute(
                """
                UPDATE airlines
                SET
                    airline_name = %s,
                    airline_code = %s,
                    country = %s
                WHERE airline_id = %s
                """,
                (
                    airline_name,
                    airline_code,
                    country,
                    airline_id
                )
            )

            db.commit()

            return redirect(url_for("admin_airlines"))

        cursor.execute(
            """
            SELECT *
            FROM airlines
            WHERE airline_id = %s
            """,
            (airline_id,)
        )

        airline = cursor.fetchone()

        if not airline:
            return redirect(url_for("admin_airlines"))

        return render_template(
            "admin_airline_form.html",
            airline=airline
        )

    except Exception as e:

        db.rollback()

        return render_template(
            "admin_airline_form.html",
            airline=None,
            error=f"Failed to update airline: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


@app.route(
    "/admin/airlines/delete/<int:airline_id>",
    methods=["POST"]
)
def admin_delete_airline(airline_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM airlines
            WHERE airline_id = %s
            """,
            (airline_id,)
        )

        db.commit()

        return redirect(url_for("admin_airlines"))

    except Exception as e:

        db.rollback()

        print("Delete airline error:", e)

        return redirect(
            url_for(
                "admin_airlines",
                error="Cannot delete this airline — it has existing flights."
            )
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# ADMIN: GATES
# ══════════════════════════════════════════════════════════

@app.route("/admin/gates")
def admin_gates():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM gates
            ORDER BY gate_number
            """
        )

        gates = cursor.fetchall()

    except Exception as e:

        gates = []

        print("Admin gates error:", e)

    finally:

        if cursor:
            cursor.close()

    return render_template(
        "admin_gates.html",
        gates=gates,
        error=request.args.get("error")
    )


@app.route(
    "/admin/gates/add",
    methods=["GET", "POST"]
)
def admin_add_gate():

    if not admin_required():
        return redirect(url_for("login"))

    if request.method == "POST":

        gate_number = request.form.get(
            "gate_number", ""
        ).strip()

        terminal = request.form.get(
            "terminal", ""
        ).strip()

        status = request.form.get(
            "status",
            "Available"
        )

        if not all([
            gate_number,
            terminal,
            status
        ]):

            return render_template(
                "admin_gate_form.html",
                gate=None,
                error="Please fill in all fields."
            )

        cursor = None

        try:

            cursor = db.cursor()

            cursor.execute(
                """
                INSERT INTO gates
                (
                    gate_number,
                    terminal,
                    status
                )
                VALUES (%s, %s, %s)
                """,
                (
                    gate_number,
                    terminal,
                    status
                )
            )

            db.commit()

            return redirect(url_for("admin_gates"))

        except Exception as e:

            db.rollback()

            return render_template(
                "admin_gate_form.html",
                gate=None,
                error=f"Failed to add gate: {str(e)}"
            )

        finally:

            if cursor:
                cursor.close()

    return render_template(
        "admin_gate_form.html",
        gate=None
    )


@app.route(
    "/admin/gates/edit/<int:gate_id>",
    methods=["GET", "POST"]
)
def admin_edit_gate(gate_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        if request.method == "POST":

            gate_number = request.form.get(
                "gate_number", ""
            ).strip()

            terminal = request.form.get(
                "terminal", ""
            ).strip()

            status = request.form.get(
                "status",
                "Available"
            )

            cursor.execute(
                """
                UPDATE gates
                SET
                    gate_number = %s,
                    terminal = %s,
                    status = %s
                WHERE gate_id = %s
                """,
                (
                    gate_number,
                    terminal,
                    status,
                    gate_id
                )
            )

            db.commit()

            return redirect(url_for("admin_gates"))

        cursor.execute(
            """
            SELECT *
            FROM gates
            WHERE gate_id = %s
            """,
            (gate_id,)
        )

        gate = cursor.fetchone()

        if not gate:
            return redirect(url_for("admin_gates"))

        return render_template(
            "admin_gate_form.html",
            gate=gate
        )

    except Exception as e:

        db.rollback()

        return render_template(
            "admin_gate_form.html",
            gate=None,
            error=f"Failed to update gate: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


@app.route(
    "/admin/gates/delete/<int:gate_id>",
    methods=["POST"]
)
def admin_delete_gate(gate_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM gates
            WHERE gate_id = %s
            """,
            (gate_id,)
        )

        db.commit()

        return redirect(url_for("admin_gates"))

    except Exception as e:

        db.rollback()

        print("Delete gate error:", e)

        return redirect(
            url_for(
                "admin_gates",
                error="Cannot delete this gate."
            )
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# ADMIN: BOOKINGS
# ══════════════════════════════════════════════════════════
@app.route("/admin/bookings")
def admin_bookings():

    if not admin_required():
        return redirect(url_for("login"))

    cursor = None

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    try:

        cursor = db.cursor(dictionary=True)

        # Get bookings (filtered by search/status if provided)
        query = """
            SELECT
                b.booking_id,
                b.booking_date,
                b.seat_number,
                b.class,
                b.amount,
                b.booking_status,
                p.passenger_id,
                u.name AS passenger_name,
                u.email AS passenger_email,
                p.phone,
                p.passport_no,
                f.flight_id,
                f.flight_number,
                f.source,
                f.destination,
                f.departure_time,
                f.arrival_time,
                f.status AS flight_status,
                a.airline_name,
                a.airline_code
            FROM bookings b
            JOIN passengers p
                ON b.passenger_id = p.passenger_id
            JOIN users u
                ON p.user_id = u.user_id
            JOIN flights f
                ON b.flight_id = f.flight_id
            JOIN airlines a
                ON f.airline_id = a.airline_id
            WHERE 1=1
        """

        params = []

        if search:
            query += """
                AND (
                    b.booking_id LIKE %s
                    OR u.name LIKE %s
                    OR u.email LIKE %s
                    OR f.flight_number LIKE %s
                )
            """
            like_term = f"%{search}%"
            params.extend([like_term, like_term, like_term, like_term])

        if status:
            query += " AND b.booking_status = %s"
            params.append(status)

        query += " ORDER BY b.booking_date DESC"

        cursor.execute(query, tuple(params))

        bookings = cursor.fetchall()

        # Total bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            """
        )

        total_bookings = cursor.fetchone()["total"]

        # Confirmed bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE booking_status = 'Confirmed'
            """
        )

        confirmed_bookings = cursor.fetchone()["total"]

        # Pending bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE booking_status = 'Pending'
            """
        )

        pending_bookings = cursor.fetchone()["total"]

        # Cancelled bookings
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE booking_status = 'Cancelled'
            """
        )

        cancelled_bookings = cursor.fetchone()["total"]

        # Revenue
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM bookings
            WHERE booking_status = 'Confirmed'
            """
        )

        total_revenue = cursor.fetchone()["total"]

        return render_template(
            "admin_bookings.html",
            bookings=bookings,
            search=search,
            status=status,
            total_bookings=total_bookings,
            confirmed_bookings=confirmed_bookings,
            pending_bookings=pending_bookings,
            cancelled_bookings=cancelled_bookings,
            total_revenue=total_revenue
        )

    except Exception as e:

        print("❌ Admin bookings error:", e)

        return render_template(
            "admin_bookings.html",
            bookings=[],
            search=search,
            status=status,
            total_bookings=0,
            confirmed_bookings=0,
            pending_bookings=0,
            cancelled_bookings=0,
            total_revenue=0,
            error=f"Unable to load bookings: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

# ══════════════════════════════════════════════════════════
# PASSENGER DASHBOARD
# ══════════════════════════════════════════════════════════
@app.route("/passenger_dashboard")
def passenger_dashboard():
    if "user_id" not in session or session["role"].lower() != "passenger":
        return redirect(url_for("login"))

    recent_bookings = []

    try:
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT passenger_id
            FROM passengers
            WHERE user_id = %s
        """, (session["user_id"],))

        passenger = cursor.fetchone()

        if passenger:

            cursor.execute("""
                SELECT
                    b.booking_id,
                    b.seat_number,
                    b.class,
                    b.booking_status,

                    f.flight_number,
                    f.source,
                    f.destination,
                    f.departure_time,

                    a.airline_name

                FROM bookings b

                JOIN flights f ON b.flight_id = f.flight_id
                JOIN airlines a ON f.airline_id = a.airline_id

                WHERE b.passenger_id = %s

                ORDER BY b.booking_date DESC
                LIMIT 3
            """, (passenger["passenger_id"],))

            recent_bookings = cursor.fetchall()

        cursor.close()

    except Exception as e:
        print("Passenger dashboard error:", e)
        recent_bookings = []

    return render_template("passenger_dashboard.html", recent_bookings=recent_bookings)
# ══════════════════════════════════════════════════════════
# SEARCH FLIGHTS
# ══════════════════════════════════════════════════════════

@app.route("/search_flights")
def search_flights():

    if not passenger_required():
        return redirect(url_for("login"))

    source = request.args.get(
        "source", ""
    ).strip()

    destination = request.args.get(
        "destination", ""
    ).strip()

    departure_date = request.args.get(
        "departure_date", ""
    ).strip()

    flights = []
    searched = False
    error = None

    if source and destination:

        searched = True

        cursor = None

        try:

            cursor = db.cursor(dictionary=True)

            query = """
                SELECT
                    f.flight_id,
                    f.flight_number,
                    f.source,
                    f.destination,
                    f.departure_time,
                    f.arrival_time,
                    f.status,
                    f.total_seats,
                    f.available_seats,
                    a.airline_name,
                    a.airline_code,
                    g.gate_number,
                    g.terminal
                FROM flights f
                JOIN airlines a
                    ON f.airline_id = a.airline_id
                LEFT JOIN gates g
                    ON f.gate_id = g.gate_id
                WHERE LOWER(f.source) = LOWER(%s)
                AND LOWER(f.destination) = LOWER(%s)
            """

            params = [
                source,
                destination
            ]

            if departure_date:

                query += """
                    AND DATE(f.departure_time) = %s
                """

                params.append(departure_date)

            query += """
                ORDER BY f.departure_time ASC
            """

            cursor.execute(
                query,
                tuple(params)
            )

            flights = cursor.fetchall()

        except Exception as e:

            print("Flight search error:", e)

            error = f"Unable to search flights: {str(e)}"

        finally:

            if cursor:
                cursor.close()

    return render_template(
        "search_flights.html",
        flights=flights,
        searched=searched,
        error=error
    )


# ══════════════════════════════════════════════════════════
# BOOK FLIGHT
# ══════════════════════════════════════════════════════════

@app.route(
    "/book_flight/<int:flight_id>",
    methods=["GET", "POST"]
)
def book_flight(flight_id):

    # User MUST be logged in as passenger
    if not passenger_required():
        return redirect(url_for("login"))

    cursor = None
    flight = None

    try:

        cursor = db.cursor(dictionary=True)

        # Get flight
        cursor.execute(
            """
            SELECT
                f.flight_id,
                f.flight_number,
                f.source,
                f.destination,
                f.departure_time,
                f.arrival_time,
                f.status,
                f.total_seats,
                f.available_seats,
                a.airline_name,
                a.airline_code,
                g.gate_number,
                g.terminal
            FROM flights f
            JOIN airlines a
                ON f.airline_id = a.airline_id
            LEFT JOIN gates g
                ON f.gate_id = g.gate_id
            WHERE f.flight_id = %s
            """,
            (flight_id,)
        )

        flight = cursor.fetchone()

        if not flight:

            return render_template(
                "search_flights.html",
                flights=[],
                searched=True,
                error="Flight not found."
            )

        # Check availability
        if flight["available_seats"] <= 0:

            return render_template(
                "search_flights.html",
                flights=[],
                searched=True,
                error="Sorry, this flight is fully booked."
            )

        # Display fare
        flight["amount"] = 5000.00

        # ── Show booking page ──────────────────────────────

        if request.method == "GET":

            return render_template(
                "book_flight.html",
                flight=flight
            )

        # ── Get form values ────────────────────────────────

        travel_class = request.form.get("class")

        seat_number = request.form.get(
            "seat_number", ""
        ).strip()

        # Validate class
        if travel_class not in [
            "Economy",
            "Business"
        ]:

            return render_template(
                "book_flight.html",
                flight=flight,
                error="Please select a valid travel class."
            )

        # Validate seat
        if not seat_number:

            return render_template(
                "book_flight.html",
                flight=flight,
                error="Please enter a seat number."
            )

        # Check existing seat
        cursor.execute(
            """
            SELECT booking_id
            FROM bookings
            WHERE flight_id = %s
            AND seat_number = %s
            AND booking_status = 'Confirmed'
            """,
            (
                flight_id,
                seat_number
            )
        )

        existing_booking = cursor.fetchone()

        if existing_booking:

            return render_template(
                "book_flight.html",
                flight=flight,
                error="This seat is already booked. Please choose another seat."
            )

        # Calculate amount
        amount = 5000.00

        if travel_class == "Business":
            amount = 8000.00

        # Get passenger ID
        cursor.execute(
            """
            SELECT passenger_id
            FROM passengers
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        passenger = cursor.fetchone()

        if not passenger:

            return render_template(
                "book_flight.html",
                flight=flight,
                error="Passenger profile not found."
            )

        passenger_id = passenger["passenger_id"]

        # Double-check seats before booking
        cursor.execute(
            """
            SELECT available_seats
            FROM flights
            WHERE flight_id = %s
            """,
            (flight_id,)
        )

        current_flight = cursor.fetchone()

        if (
            not current_flight
            or current_flight["available_seats"] <= 0
        ):

            return render_template(
                "book_flight.html",
                flight=flight,
                error="Sorry, no seats are available."
            )

        # Insert booking
        cursor.execute(
            """
            INSERT INTO bookings
            (
                passenger_id,
                flight_id,
                booking_date,
                seat_number,
                class,
                amount,
                booking_status
            )
            VALUES
            (%s, %s, NOW(), %s, %s, %s, 'Confirmed')
            """,
            (
                passenger_id,
                flight_id,
                seat_number,
                travel_class,
                amount
            )
        )

        # Get booking ID immediately after INSERT
        booking_id = cursor.lastrowid

        # Decrease available seats
        cursor.execute(
            """
            UPDATE flights
            SET available_seats = available_seats - 1
            WHERE flight_id = %s
            AND available_seats > 0
            """,
            (flight_id,)
        )

        if cursor.rowcount != 1:

            db.rollback()

            return render_template(
                "book_flight.html",
                flight=flight,
                error="Unable to reserve the seat. Please try again."
            )

        db.commit()

        # ──────────────────────────────────────────────────
        # FIX:
        # Do NOT render login.html here.
        #
        # Store success message in session and redirect
        # to My Bookings while keeping the user logged in.
        # ──────────────────────────────────────────────────

        session["booking_success"] = (
            f"Booking confirmed successfully! "
            f"Booking ID: {booking_id}"
        )

        return redirect(url_for("my_bookings"))

    except Exception as e:

        db.rollback()

        print("Booking error:", e)

        return render_template(
            "book_flight.html",
            flight=flight,
            error=f"Booking failed: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# MY BOOKINGS
# ══════════════════════════════════════════════════════════

@app.route("/my_bookings")
def my_bookings():

    if not passenger_required():
        return redirect(url_for("login"))

    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        # Get passenger ID
        cursor.execute(
            """
            SELECT passenger_id
            FROM passengers
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        passenger = cursor.fetchone()

        if not passenger:

            return render_template(
                "my_bookings.html",
                bookings=[],
                confirmed_count=0,
                cancelled_count=0,
                error="Passenger profile not found."
            )

        passenger_id = passenger["passenger_id"]

        # Get bookings
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.booking_date,
                b.seat_number,
                b.class,
                b.amount,
                b.booking_status,
                f.flight_id,
                f.flight_number,
                f.source,
                f.destination,
                f.departure_time,
                f.arrival_time,
                f.status AS flight_status,
                a.airline_name,
                a.airline_code,
                g.gate_number,
                g.terminal
            FROM bookings b
            JOIN flights f
                ON b.flight_id = f.flight_id
            JOIN airlines a
                ON f.airline_id = a.airline_id
            LEFT JOIN gates g
                ON f.gate_id = g.gate_id
            WHERE b.passenger_id = %s
            ORDER BY b.booking_date DESC
            """,
            (passenger_id,)
        )

        bookings = cursor.fetchall()

        # Confirmed count
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM bookings
            WHERE passenger_id = %s
            AND booking_status = 'Confirmed'
            """,
            (passenger_id,)
        )

        confirmed_count = cursor.fetchone()["count"]

        # Cancelled count
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM bookings
            WHERE passenger_id = %s
            AND booking_status = 'Cancelled'
            """,
            (passenger_id,)
        )

        cancelled_count = cursor.fetchone()["count"]

        # Get success message created after booking
        success = session.pop("booking_success", None)

        return render_template(
            "my_bookings.html",
            bookings=bookings,
            confirmed_count=confirmed_count,
            cancelled_count=cancelled_count,
            success=success
        )

    except Exception as e:

        print("My bookings error:", e)

        return render_template(
            "my_bookings.html",
            bookings=[],
            confirmed_count=0,
            cancelled_count=0,
            error=f"Unable to load bookings: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()


# ══════════════════════════════════════════════════════════
# CANCEL BOOKING
# ══════════════════════════════════════════════════════════

@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if not passenger_required():
        return redirect(url_for("login"))

    cursor = None

    try:
        cursor = db.cursor(dictionary=True)

        # Verify that this booking belongs to the logged-in passenger
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.flight_id,
                b.booking_status
            FROM bookings b
            JOIN passengers p
                ON b.passenger_id = p.passenger_id
            WHERE b.booking_id = %s
            AND p.user_id = %s
            """,
            (
                booking_id,
                session["user_id"]
            )
        )

        booking = cursor.fetchone()

        if not booking:
            return redirect(url_for("my_bookings"))

        # Cancel only confirmed bookings
        if booking["booking_status"] == "Confirmed":

            cursor.execute(
                """
                UPDATE bookings
                SET booking_status = 'Cancelled'
                WHERE booking_id = %s
                AND booking_status = 'Confirmed'
                """,
                (booking_id,)
            )

            if cursor.rowcount == 1:

                # Return the seat to available seats
                cursor.execute(
                    """
                    UPDATE flights
                    SET available_seats = available_seats + 1
                    WHERE flight_id = %s
                    """,
                    (booking["flight_id"],)
                )

                db.commit()

        return redirect(url_for("my_bookings"))

    except Exception as e:

        db.rollback()

        print("Cancel booking error:", e)

        return redirect(url_for("my_bookings"))

    finally:

        if cursor:
            cursor.close()
# ══════════════════════════════════════════════════════════
# FLIGHT STATUS
# ══════════════════════════════════════════════════════════

@app.route(
    "/flight_status",
    methods=["GET", "POST"]
)
def flight_status():

    if not passenger_required():
        return redirect(url_for("login"))

    flight = None
    searched = False
    error = None

    if request.method == "POST":

        flight_number = request.form.get(
            "flight_number", ""
        ).strip()

        searched = True

        if not flight_number:

            error = "Please enter a flight number."

        else:

            cursor = None

            try:

                cursor = db.cursor(dictionary=True)

                cursor.execute(
                    """
                    SELECT
                        f.flight_id,
                        f.flight_number,
                        f.source,
                        f.destination,
                        f.departure_time,
                        f.arrival_time,
                        f.status,
                        f.total_seats,
                        f.available_seats,
                        a.airline_name,
                        a.airline_code,
                        g.gate_number,
                        g.terminal
                    FROM flights f
                    JOIN airlines a
                        ON f.airline_id = a.airline_id
                    LEFT JOIN gates g
                        ON f.gate_id = g.gate_id
                    WHERE UPPER(f.flight_number) = UPPER(%s)
                    """,
                    (flight_number,)
                )

                flight = cursor.fetchone()

                if not flight:
                    error = "No flight found with that flight number."

            except Exception as e:

                error = f"Unable to check status: {str(e)}"

            finally:

                if cursor:
                    cursor.close()

    return render_template(
        "flight_status.html",
        flight=flight,
        searched=searched,
        error=error
    )


# ══════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    if not passenger_required():
        return redirect(url_for("login"))

    error = None
    success = None
    passenger = None
    cursor = None

    try:

        cursor = db.cursor(dictionary=True)

        if request.method == "POST":

            phone = request.form.get(
                "phone", ""
            ).strip()

            gender = request.form.get(
                "gender", ""
            ).strip()

            date_of_birth = request.form.get(
                "date_of_birth", ""
            ).strip()

            if not phone:

                error = "Phone number is required."

            else:

                cursor.execute(
                    """
                    UPDATE passengers
                    SET
                        phone = %s,
                        gender = %s,
                        date_of_birth = %s
                    WHERE user_id = %s
                    """,
                    (
                        phone,
                        gender,
                        date_of_birth,
                        session["user_id"]
                    )
                )

                db.commit()

                success = "Profile updated successfully!"

        # Get passenger profile
        cursor.execute(
            """
            SELECT
                u.name,
                u.email,
                p.phone,
                p.gender,
                p.date_of_birth,
                p.passport_no
            FROM users u
            JOIN passengers p
                ON u.user_id = p.user_id
            WHERE u.user_id = %s
            """,
            (session["user_id"],)
        )

        passenger = cursor.fetchone()

    except Exception as e:

        db.rollback()

        error = f"Unable to load profile: {str(e)}"

    finally:

        if cursor:
            cursor.close()

    return render_template(
        "profile.html",
        passenger=passenger,
        error=error,
        success=success
    )
# ── Admin: Passengers ─────────────────────────────────────

@app.route("/admin/passengers")
def admin_passengers():
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    try:
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT
                p.passenger_id, p.phone, p.gender, p.date_of_birth, p.passport_no,
                u.user_id, u.name, u.email,
                COUNT(b.booking_id) AS total_bookings
            FROM passengers p
            JOIN users u ON p.user_id = u.user_id
            LEFT JOIN bookings b ON b.passenger_id = p.passenger_id
            WHERE 1=1
        """

        params = []

        if search:
            query += " AND (u.name LIKE %s OR u.email LIKE %s OR p.passport_no LIKE %s)"
            like_term = f"%{search}%"
            params.extend([like_term, like_term, like_term])

        query += " GROUP BY p.passenger_id ORDER BY u.name ASC"

        cursor.execute(query, tuple(params))
        passengers = cursor.fetchall()

        cursor.close()

    except Exception as e:
        print("Admin passengers error:", e)
        passengers = []

    return render_template("admin_passengers.html", passengers=passengers, search=search)


# ── Admin: Employees ──────────────────────────────────────

@app.route("/admin/employees")
def admin_employees():
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM employees ORDER BY name ASC")
        employees = cursor.fetchall()
        cursor.close()
    except Exception as e:
        employees = []
        print("Admin employees error:", e)

    return render_template("admin_employees.html", employees=employees, error=request.args.get("error"))


@app.route("/admin/employees/add", methods=["GET", "POST"])
def admin_add_employee():
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        position = request.form.get("position", "").strip()
        salary = request.form.get("salary", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not all([name, department, position, salary, phone, email]):
            return render_template("admin_employee_form.html", employee=None, error="Please fill in all fields.")

        try:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO employees (name, department, position, salary, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, department, position, salary, phone, email))
            db.commit()
            cursor.close()
            return redirect(url_for("admin_employees"))

        except Exception as e:
            db.rollback()
            return render_template("admin_employee_form.html", employee=None, error=f"Failed to add employee: {str(e)}")

    return render_template("admin_employee_form.html", employee=None)


@app.route("/admin/employees/edit/<int:employee_id>", methods=["GET", "POST"])
def admin_edit_employee(employee_id):
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        position = request.form.get("position", "").strip()
        salary = request.form.get("salary", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        try:
            cursor.execute("""
                UPDATE employees
                SET name = %s, department = %s, position = %s,
                    salary = %s, phone = %s, email = %s
                WHERE employee_id = %s
            """, (name, department, position, salary, phone, email, employee_id))
            db.commit()
            cursor.close()
            return redirect(url_for("admin_employees"))

        except Exception as e:
            db.rollback()
            cursor.close()
            return render_template("admin_employee_form.html", employee=None, error=f"Failed to update employee: {str(e)}")

    cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()
    cursor.close()

    if not employee:
        return redirect(url_for("admin_employees"))

    return render_template("admin_employee_form.html", employee=employee)


@app.route("/admin/employees/delete/<int:employee_id>", methods=["POST"])
def admin_delete_employee(employee_id):
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
        db.commit()
        cursor.close()
        return redirect(url_for("admin_employees"))

    except Exception as e:
        db.rollback()
        return redirect(url_for("admin_employees", error="Failed to delete employee."))

@app.route("/admin/reports")
def admin_reports():
    if "user_id" not in session or session["role"].lower() != "admin":
        return redirect(url_for("login"))

    try:
        cursor = db.cursor(dictionary=True)

        # Revenue by month (last 6 months, confirmed bookings only)
        cursor.execute("""
            SELECT
                DATE_FORMAT(booking_date, '%%Y-%%m') AS month,
                SUM(amount) AS revenue
            FROM bookings
            WHERE booking_status = 'Confirmed'
              AND booking_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY month
            ORDER BY month ASC
        """)
        revenue_rows = cursor.fetchall()
        revenue_labels = [row["month"] for row in revenue_rows]
        revenue_values = [float(row["revenue"]) for row in revenue_rows]

        # Bookings trend by day (last 30 days)
        cursor.execute("""
            SELECT
                DATE(booking_date) AS day,
                COUNT(*) AS count
            FROM bookings
            WHERE booking_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY day
            ORDER BY day ASC
        """)
        trend_rows = cursor.fetchall()
        trend_labels = [row["day"].strftime("%d %b") for row in trend_rows]
        trend_values = [row["count"] for row in trend_rows]

        # Bookings by status
        cursor.execute("""
            SELECT booking_status, COUNT(*) AS count
            FROM bookings
            GROUP BY booking_status
        """)
        status_rows = cursor.fetchall()
        status_labels = [row["booking_status"] for row in status_rows]
        status_values = [row["count"] for row in status_rows]

        # Top 5 routes by bookings
        cursor.execute("""
            SELECT
                CONCAT(f.source, ' → ', f.destination) AS route,
                COUNT(*) AS count
            FROM bookings b
            JOIN flights f ON b.flight_id = f.flight_id
            WHERE b.booking_status = 'Confirmed'
            GROUP BY f.source, f.destination
            ORDER BY count DESC
            LIMIT 5
        """)
        route_rows = cursor.fetchall()
        route_labels = [row["route"] for row in route_rows]
        route_values = [row["count"] for row in route_rows]

        # Bookings by class
        cursor.execute("""
            SELECT class, COUNT(*) AS count
            FROM bookings
            WHERE booking_status = 'Confirmed'
            GROUP BY class
        """)
        class_rows = cursor.fetchall()
        class_labels = [row["class"] for row in class_rows]
        class_values = [row["count"] for row in class_rows]

        # Summary numbers
        cursor.execute("SELECT SUM(amount) AS total FROM bookings WHERE booking_status = 'Confirmed'")
        result = cursor.fetchone()["total"]
        total_revenue = float(result) if result else 0.0

        cursor.execute("SELECT COUNT(*) AS count FROM bookings WHERE booking_status = 'Confirmed'")
        total_confirmed = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT AVG(amount) AS avg_amount
            FROM bookings
            WHERE booking_status = 'Confirmed'
        """)
        result = cursor.fetchone()["avg_amount"]
        avg_booking_value = float(result) if result else 0.0

        cursor.close()

    except Exception as e:
        print("Admin reports error:", e)
        revenue_labels = revenue_values = []
        trend_labels = trend_values = []
        status_labels = status_values = []
        route_labels = route_values = []
        class_labels = class_values = []
        total_revenue = total_confirmed = avg_booking_value = 0

    return render_template(
        "admin_reports.html",
        revenue_labels=revenue_labels,
        revenue_values=revenue_values,
        trend_labels=trend_labels,
        trend_values=trend_values,
        status_labels=status_labels,
        status_values=status_values,
        route_labels=route_labels,
        route_values=route_values,
        class_labels=class_labels,
        class_values=class_values,
        total_revenue=total_revenue,
        total_confirmed=total_confirmed,
        avg_booking_value=avg_booking_value
    )

# ══════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════
# RUN APPLICATION
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":

    create_default_admin()

    app.run(
        debug=False,
        use_reloader=False
    )