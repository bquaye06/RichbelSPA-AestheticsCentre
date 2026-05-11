from flask import Flask, render_template, jsonify, request
from flask import redirect, session, flash, url_for
from flask_cors import CORS
import os
import re
import requests
from dotenv import load_dotenv
from datetime import datetime
from uuid import UUID
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from config import config
from utils.sms import send_sms

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

# Load config
env = os.getenv("FLASK_ENV", "development")
app.config.from_object(config[env])

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

SUPABASE_URL = app.config.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = app.config.get("SUPABASE_SERVICE_KEY")
ADMIN_EMAIL = app.config.get("ADMIN_EMAIL", "rhichbelspaandaesthetics@gmail.com")
ADMIN_DEFAULT_PASSWORD = app.config.get("ADMIN_DEFAULT_PASSWORD", "Rhichbel@123")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}


def supabase_request(method, path, params=None, payload=None, prefer_return=False):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = dict(SUPABASE_HEADERS)
    if prefer_return:
        headers["Prefer"] = "return=representation"

    response = requests.request(method, url, headers=headers, params=params, json=payload, timeout=10)
    return response


def get_admin_record():
    response = supabase_request(
        "GET",
        "admin_credentials",
        params={"email": f"eq.{ADMIN_EMAIL}", "select": "id,email,password_hash,updated_at"},
    )
    response.raise_for_status()
    data = response.json() or []
    return data[0] if data else None


def ensure_admin_record():
    record = get_admin_record()
    if record:
        return record

    create_response = supabase_request(
        "POST",
        "admin_credentials",
        payload={
            "email": ADMIN_EMAIL,
            "password_hash": generate_password_hash(ADMIN_DEFAULT_PASSWORD),
        },
        prefer_return=True,
    )
    create_response.raise_for_status()
    created = create_response.json() or []
    return created[0] if isinstance(created, list) and created else created


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def fetch_bookable_services():
    response = supabase_request(
        "GET",
        "service_variants",
        params={
            "select": "id,variant_name,unit_type,quantity,min_sessions,max_sessions,notes,is_active,services(name,slug),service_prices(*)",
            "is_active": "eq.true",
        },
    )
    response.raise_for_status()
    data = response.json() or []

    variants = []
    for v in data:
        prices = v.get("service_prices") or []
        latest = max(prices, key=lambda p: p.get("effective_from", ""), default=None)
        if latest or request.args.get("bookable", "true").lower() == "false":
            variants.append({
                "variant_id": v["id"],
                "service_name": v.get("services", {}).get("name"),
                "service_slug": v.get("services", {}).get("slug"),
                "variant_name": v.get("variant_name"),
                "unit_type": v.get("unit_type"),
                "quantity": v.get("quantity"),
                "min_sessions": v.get("min_sessions"),
                "max_sessions": v.get("max_sessions"),
                "notes": v.get("notes"),
                "latest_price": latest,
            })

    return variants


def fetch_appointments():
    response = supabase_request(
        "GET",
        "appointments",
        params={
            "select": "id,first_name,last_name,email,phone,appointment_date,appointment_time,status,notes,created_at,updated_at,service_variant_id,service_variants(id,variant_name,services(name,slug))",
            "order": "appointment_date.desc,appointment_time.desc",
        },
    )
    response.raise_for_status()
    data = response.json() or []
    return [normalize_appointment_record(record) for record in data]


def normalize_appointment_record(record):
    service_variant = record.get("service_variants") or {}
    if isinstance(service_variant, list):
        service_variant = service_variant[0] if service_variant else {}

    service_object = service_variant.get("services") or {}
    if isinstance(service_object, list):
        service_object = service_object[0] if service_object else {}

    service_name = service_object.get("name") or "Unknown Service"
    variant_name = service_variant.get("variant_name") or "Standard Option"

    normalized = dict(record)
    normalized["service_label"] = f"{service_name} - {variant_name}"
    normalized["service_name"] = service_name
    normalized["variant_name"] = variant_name
    return normalized


def fetch_appointment_by_id(appointment_id):
    response = supabase_request(
        "GET",
        "appointments",
        params={
            "id": f"eq.{appointment_id}",
            "select": "id,first_name,last_name,email,phone,appointment_date,appointment_time,status,notes,created_at,updated_at,service_variant_id,service_variants(id,variant_name,services(name,slug))",
        },
    )
    response.raise_for_status()
    data = response.json() or []
    return normalize_appointment_record(data[0]) if data else None


def fetch_service_label_by_variant_id(service_variant_id):
    response = supabase_request(
        "GET",
        "service_variants",
        params={
            "id": f"eq.{service_variant_id}",
            "select": "variant_name,services(name)",
        },
    )
    response.raise_for_status()
    data = response.json() or []
    if not data:
        return None

    service_variant = data[0] or {}
    service_object = service_variant.get("services") or {}
    if isinstance(service_object, list):
        service_object = service_object[0] if service_object else {}

    service_name = service_object.get("name") or "Unknown Service"
    variant_name = service_variant.get("variant_name") or "Standard Option"
    return f"{service_name} - {variant_name}"

# Routes
@app.route("/")
@app.route("/home")
def home():
    """Serve homepage."""
    return render_template("index.html")

@app.route("/services")
def services():
    """Serve services page."""
    return render_template("services.html")

@app.route("/gallery")
def gallery():
    """Serve gallery page."""
    return render_template("gallery.html")

@app.route("/about")
def about():
    """Serve about page."""
    return render_template("about.html")

@app.route("/contact")
def contact():
    """Serve contact page."""
    return render_template("contact.html")

@app.route("/appointment")
def appointment():
    """Serve the appointment booking page."""
    return render_template("appointment.html", hide_booking_modal=True)

@app.route("/admin")
def admin_root():
    return redirect(url_for("admin_dashboard") if session.get("admin_authenticated") else url_for("admin_login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ensure_admin_record()

    if request.method == "POST" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        email = str(request.form.get("email") or (request.get_json(silent=True) or {}).get("email") or "").strip().lower()
        password = str(request.form.get("password") or (request.get_json(silent=True) or {}).get("password") or "")

        if email != ADMIN_EMAIL.lower():
            flash("Invalid admin credentials.", "error")
            return render_template("admin_login.html", admin_email=ADMIN_EMAIL), 401

        try:
            admin_record = get_admin_record() or ensure_admin_record()
        except Exception as exc:
            flash(f"Unable to verify admin account: {exc}", "error")
            return render_template("admin_login.html", admin_email=ADMIN_EMAIL), 500

        if not admin_record or not check_password_hash(admin_record.get("password_hash", ""), password):
            flash("Invalid admin credentials.", "error")
            return render_template("admin_login.html", admin_email=ADMIN_EMAIL), 401

        session["admin_authenticated"] = True
        session["admin_email"] = ADMIN_EMAIL
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html", admin_email=ADMIN_EMAIL)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    session.pop("admin_email", None)
    flash("You have been signed out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    appointments = fetch_appointments()
    counts = {"total": len(appointments), "pending": 0, "confirmed": 0, "completed": 0, "cancelled": 0}

    for appointment_record in appointments:
        status = (appointment_record.get("status") or "pending").lower()
        if status in counts:
            counts[status] += 1

    return render_template(
        "admin_dashboard.html",
        appointments=appointments,
        stats=counts,
        admin_email=session.get("admin_email", ADMIN_EMAIL),
    )


@app.route("/admin/appointments/<appointment_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_appointment(appointment_id):
    try:
        UUID(appointment_id)
    except ValueError:
        flash("Invalid appointment selected.", "error")
        return redirect(url_for("admin_dashboard"))

    appointment_record = fetch_appointment_by_id(appointment_id)
    if not appointment_record:
        flash("Appointment not found.", "error")
        return redirect(url_for("admin_dashboard"))

    services = fetch_bookable_services()

    if request.method == "POST":
        form = request.form
        update_payload = {
            "first_name": str(form.get("first_name", "")).strip(),
            "last_name": str(form.get("last_name", "")).strip(),
            "email": str(form.get("email", "")).strip(),
            "phone": str(form.get("phone", "")).strip(),
            "appointment_date": str(form.get("appointment_date", "")).strip(),
            "appointment_time": str(form.get("appointment_time", "")).strip(),
            "status": str(form.get("status", "pending")).strip(),
            "notes": str(form.get("notes", "")).strip() or None,
        }

        service_variant_id = str(form.get("service_variant_id", "")).strip()
        if service_variant_id:
            try:
                UUID(service_variant_id)
            except ValueError:
                flash("Invalid service selected.", "error")
                return render_template("admin_edit_appointment.html", appointment=appointment_record, services=services, admin_email=session.get("admin_email", ADMIN_EMAIL))
            update_payload["service_variant_id"] = service_variant_id

        missing_fields = [field for field in ["first_name", "last_name", "email", "phone", "appointment_date", "appointment_time"] if not update_payload[field]]
        if missing_fields:
            flash("Please complete all required fields.", "error")
            return render_template("admin_edit_appointment.html", appointment=appointment_record, services=services, admin_email=session.get("admin_email", ADMIN_EMAIL))

        try:
            datetime.strptime(update_payload["appointment_date"], "%Y-%m-%d")
            time_match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", update_payload["appointment_time"])
            if not time_match:
                raise ValueError("Invalid time")
            update_payload["appointment_time"] = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        except ValueError:
            flash("Use a valid date and time format like 2026-05-12 and 09:30.", "error")
            return render_template("admin_edit_appointment.html", appointment=appointment_record, services=services, admin_email=session.get("admin_email", ADMIN_EMAIL))

        update_response = supabase_request(
            "PATCH",
            "appointments",
            params={"id": f"eq.{appointment_id}"},
            payload=update_payload,
        )
        if not update_response.ok:
            flash("Unable to update appointment.", "error")
            return render_template("admin_edit_appointment.html", appointment=appointment_record, services=services, admin_email=session.get("admin_email", ADMIN_EMAIL))

        flash("Appointment updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit_appointment.html", appointment=appointment_record, services=services, admin_email=session.get("admin_email", ADMIN_EMAIL))


@app.route("/admin/appointments/<appointment_id>/status", methods=["POST"])
@admin_required
def admin_update_appointment_status(appointment_id):
    status = str(request.form.get("status", "")).strip().lower()
    if status not in {"pending", "confirmed", "completed", "cancelled"}:
        flash("Invalid status.", "error")
        return redirect(url_for("admin_dashboard"))

    response = supabase_request(
        "PATCH",
        "appointments",
        params={"id": f"eq.{appointment_id}"},
        payload={"status": status},
    )
    if not response.ok:
        flash("Unable to update appointment status.", "error")
    else:
        flash("Appointment status updated.", "success")
        # notify client about status change (best-effort)
        try:
            appt = fetch_appointment_by_id(appointment_id)
            if appt:
                phone = appt.get("phone")
                first = appt.get("first_name", "")
                appointment_date = appt.get("appointment_date")
                appointment_time = appt.get("appointment_time")
                service_label = appt.get("service_label") or "your appointment"
                status_readable = status.capitalize()
                if phone:
                    msg = f"Hello {first}, your {service_label} appointment on {appointment_date} at {appointment_time} is now {status_readable}. Please call for more information."
                    ok, details = send_sms(phone, msg)
                    if not ok:
                        app.logger.warning("SMS send failed for status update %s: %s", appointment_id, details)
        except Exception as exc:
            app.logger.exception("Error sending SMS for status update: %s", exc)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/appointments/<appointment_id>/cancel", methods=["POST"])
@admin_required
def admin_cancel_appointment(appointment_id):
    response = supabase_request(
        "PATCH",
        "appointments",
        params={"id": f"eq.{appointment_id}"},
        payload={"status": "cancelled"},
    )
    if not response.ok:
        flash("Unable to cancel appointment.", "error")
    else:
        flash("Appointment cancelled.", "success")
        # notify client about cancellation (best-effort)
        try:
            appt = fetch_appointment_by_id(appointment_id)
            if appt:
                phone = appt.get("phone")
                first = appt.get("first_name", "")
                appointment_date = appt.get("appointment_date")
                appointment_time = appt.get("appointment_time")
                service_label = appt.get("service_label") or "your appointment"
                if phone:
                    msg = f"Hello {first}, your {service_label} appointment on {appointment_date} at {appointment_time} has been cancelled."
                    ok, details = send_sms(phone, msg)
                    if not ok:
                        app.logger.warning("SMS send failed for cancel %s: %s", appointment_id, details)
        except Exception as exc:
            app.logger.exception("Error sending SMS for cancellation: %s", exc)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/appointments/<appointment_id>/delete", methods=["POST"])
@admin_required
def admin_delete_appointment(appointment_id):
    response = supabase_request(
        "DELETE",
        "appointments",
        params={"id": f"eq.{appointment_id}"},
    )
    if not response.ok:
        flash("Unable to delete appointment.", "error")
    else:
        flash("Appointment deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    admin_record = get_admin_record() or ensure_admin_record()

    if request.method == "POST":
        current_password = str(request.form.get("current_password", ""))
        new_password = str(request.form.get("new_password", ""))
        confirm_password = str(request.form.get("confirm_password", ""))

        if not check_password_hash(admin_record.get("password_hash", ""), current_password):
            flash("Current password is incorrect.", "error")
            return render_template("admin_settings.html", admin_email=ADMIN_EMAIL)

        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
            return render_template("admin_settings.html", admin_email=ADMIN_EMAIL)

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("admin_settings.html", admin_email=ADMIN_EMAIL)

        update_response = supabase_request(
            "PATCH",
            "admin_credentials",
            params={"email": f"eq.{ADMIN_EMAIL}"},
            payload={"password_hash": generate_password_hash(new_password), "updated_at": datetime.utcnow().isoformat()},
        )
        if not update_response.ok:
            flash("Unable to update password.", "error")
            return render_template("admin_settings.html", admin_email=ADMIN_EMAIL)

        flash("Password updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_settings.html", admin_email=ADMIN_EMAIL)

@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

@app.route("/api/services", methods=["GET"])
def api_services():
    """Fetch bookable services from Supabase."""
    try:
        return jsonify(fetch_bookable_services())
    except requests.HTTPError as e:
        return jsonify({"error": "failed to fetch from supabase", "details": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "internal server error", "details": str(e)}), 500

@app.route("/api/admin/appointments", methods=["GET"])
@admin_required
def api_admin_appointments():
    """Fetch all appointments and stats for the dashboard (used for live refresh)."""
    try:
        appointments = fetch_appointments()
        counts = {"total": len(appointments), "pending": 0, "confirmed": 0, "completed": 0, "cancelled": 0}
        
        for appointment_record in appointments:
            status = (appointment_record.get("status") or "pending").lower()
            if status in counts:
                counts[status] += 1
        
        return jsonify({
            "appointments": appointments,
            "stats": counts
        }), 200
    except requests.HTTPError as e:
        return jsonify({"error": "failed to fetch from supabase", "details": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "internal server error", "details": str(e)}), 500

@app.route("/api/appointments", methods=["POST"])
def api_appointments():
    """Create an appointment in Supabase."""
    payload = request.get_json(silent=True) or {}
    required_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "service_variant_id",
        "appointment_date",
        "appointment_time",
    ]

    missing_fields = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing_fields:
        return jsonify({"error": "missing required fields", "fields": missing_fields}), 400

    service_variant_id = str(payload.get("service_variant_id", "")).strip()
    try:
        UUID(service_variant_id)
    except ValueError:
        return jsonify({"error": "invalid service_variant_id"}), 400

    try:
        datetime.strptime(payload["appointment_date"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid appointment date format"}), 400

    appointment_time_raw = str(payload.get("appointment_time", "")).strip()
    time_match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", appointment_time_raw)
    if not time_match:
        return jsonify({"error": "invalid appointment time format", "hint": "Use HH:MM, for example 09:30 or 17:00"}), 400

    appointment_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

    insert_payload = {
        "first_name": str(payload.get("first_name", "")).strip(),
        "last_name": str(payload.get("last_name", "")).strip(),
        "email": str(payload.get("email", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "service_variant_id": service_variant_id,
        "appointment_date": payload["appointment_date"],
        "appointment_time": appointment_time,
        "notes": str(payload.get("notes", "")).strip() or None,
        "status": "pending",
    }

    try:
        url = f"{SUPABASE_URL}/rest/v1/appointments"
        headers = {**SUPABASE_HEADERS, "Prefer": "return=representation"}
        resp = requests.post(url, headers=headers, json=insert_payload, timeout=10)
        if not resp.ok:
            details = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            return jsonify({"error": "failed to create appointment", "details": details}), resp.status_code

        created = resp.json()
        created_rec = created[0] if isinstance(created, list) and created else created
        # attempt to notify the client via SMS (best-effort)
        try:
            phone = (created_rec or {}).get("phone")
            first = (created_rec or {}).get("first_name", "")
            service_label = fetch_service_label_by_variant_id(service_variant_id) or "your booking"
            appointment_date = (created_rec or {}).get("appointment_date")
            appointment_time = (created_rec or {}).get("appointment_time")
            if phone:
                msg = f"Hi {first}, thanks for booking {service_label} on {appointment_date} at {appointment_time}. Please confirm by calling us."
                ok, details = send_sms(phone, msg)
                if not ok:
                    app.logger.warning("SMS send failed for new appointment %s: %s", created_rec.get("id"), details)
        except Exception as exc:
            app.logger.exception("Error while sending SMS after appointment create: %s", exc)

        return jsonify({"message": "appointment created", "appointment": created_rec}), 201
    except Exception as e:
        return jsonify({"error": "internal server error", "details": str(e)}), 500

# WSGI entry point for Gunicorn / Render.
application = app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
