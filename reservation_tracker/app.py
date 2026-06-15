import calendar
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
import database

app = Flask(__name__)
app.secret_key = "imfinity-tracker-2025-secret"

USERNAME = "admin"
PASSWORD = "imfinity2025"

WEEKDAY_HOURS = list(range(16, 21))   # 16:00 – 20:00 (last slot, ends 21:00)
WEEKEND_HOURS = list(range(13, 21))   # 13:00 – 20:00

SERVICES = ["Kontrola", "Botox", "Usta", "Kolagen"]

MONTHS_SR = ["", "Januar", "Februar", "Mart", "April", "Maj", "Jun",
             "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]

DAYS_SHORT_SR = ["Pon", "Uto", "Sre", "Čet", "Pet", "Sub", "Ned"]
DAYS_LONG_SR  = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]

database.init_db()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("calendar_view"))
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("calendar_view"))
        flash("Pogrešno korisničko ime ili lozinka.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Calendar ──────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return redirect(url_for("calendar_view"))


@app.route("/calendar")
@app.route("/calendar/<int:year>/<int:month>")
@login_required
def calendar_view(year=None, month=None):
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    month_res = database.get_by_month(year, month)
    res_by_date = {}
    for r in month_res:
        res_by_date.setdefault(r["date"], []).append(r)

    cal = calendar.monthcalendar(year, month)

    prev_month = month - 1 or 12
    prev_year  = year - 1 if month == 1 else year
    next_month = month % 12 + 1
    next_year  = year + 1 if month == 12 else year

    return render_template("calendar.html",
        cal=cal,
        year=year, month=month,
        month_name=MONTHS_SR[month],
        day_headers=DAYS_SHORT_SR,
        today=today.isoformat(),
        res_by_date=res_by_date,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
    )


# ── Day view ──────────────────────────────────────────────────────────────────

@app.route("/day/<date_str>")
@login_required
def day_view(date_str):
    try:
        day_date = date.fromisoformat(date_str)
    except ValueError:
        return redirect(url_for("calendar_view"))

    reservations = database.get_by_date(date_str)
    weekday = day_date.weekday()
    hours   = WEEKEND_HOURS if weekday >= 5 else WEEKDAY_HOURS
    booked  = {r["time"]: r for r in reservations}

    slots = [{"time": f"{h:02d}:00", "reservation": booked.get(f"{h:02d}:00")} for h in hours]

    return render_template("day.html",
        date_str=date_str,
        day_name=DAYS_LONG_SR[weekday],
        formatted_date=day_date.strftime("%d.%m.%Y."),
        slots=slots,
        year=day_date.year,
        month=day_date.month,
    )


# ── Booking form ──────────────────────────────────────────────────────────────

@app.route("/add", methods=["GET", "POST"])
@app.route("/add/<prefill_date>/<prefill_time>", methods=["GET", "POST"])
@login_required
def add(prefill_date=None, prefill_time=None):
    if request.method == "POST":
        client_name  = request.form["client_name"].strip()
        date_        = request.form["date"]
        time_        = request.form["time"]
        service_sel  = request.form.get("service_select", "")
        service_cust = request.form.get("service_custom", "").strip()
        service_type = service_cust if service_sel == "other" else service_sel
        notes        = request.form.get("notes", "").strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Molimo popunite sva obavezna polja.", "error")
            return render_template("form.html", action="Dodaj", services=SERVICES,
                                   prefill={"date": date_, "time": time_,
                                            "client_name": client_name,
                                            "notes": notes, "service_type": service_type})
        database.add(client_name, date_, time_, service_type, notes)
        flash(f"Termin za {client_name} je zakazan. ✓", "success")
        return redirect(url_for("day_view", date_str=date_))

    return render_template("form.html", action="Dodaj", services=SERVICES,
                           prefill={"date": prefill_date or "", "time": prefill_time or ""})


@app.route("/edit/<int:res_id>", methods=["GET", "POST"])
@login_required
def edit(res_id):
    reservation = database.get_by_id(res_id)
    if not reservation:
        flash("Termin nije pronađen.", "error")
        return redirect(url_for("calendar_view"))

    if request.method == "POST":
        client_name  = request.form["client_name"].strip()
        date_        = request.form["date"]
        time_        = request.form["time"]
        service_sel  = request.form.get("service_select", "")
        service_cust = request.form.get("service_custom", "").strip()
        service_type = service_cust if service_sel == "other" else service_sel
        notes        = request.form.get("notes", "").strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Molimo popunite sva obavezna polja.", "error")
            return render_template("form.html", action="Izmeni", services=SERVICES,
                                   res_id=res_id, prefill=dict(request.form))
        database.update(res_id, client_name, date_, time_, service_type, notes)
        flash(f"Termin za {client_name} je izmenjen. ✓", "success")
        return redirect(url_for("day_view", date_str=date_))

    return render_template("form.html", action="Izmeni", services=SERVICES,
                           res_id=res_id, prefill=dict(reservation))


@app.route("/delete/<int:res_id>", methods=["POST"])
@login_required
def delete(res_id):
    res = database.get_by_id(res_id)
    back_date = res["date"] if res else None
    if res:
        database.delete(res_id)
        flash(f"Termin za {res['client_name']} je obrisan.", "success")
    if back_date:
        return redirect(url_for("day_view", date_str=back_date))
    return redirect(url_for("calendar_view"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
