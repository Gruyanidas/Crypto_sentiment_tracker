import os
import calendar
from datetime import date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
import database

app = Flask(__name__)
# Production values are provided via environment variables (set on the host);
# the fallbacks keep local development working.
app.secret_key = os.environ.get("SECRET_KEY", "dermaplus-tracker-2025-secret")

USERNAME = os.environ.get("APP_USERNAME", "admin")
PASSWORD = os.environ.get("APP_PASSWORD", "dermaplus2025")

WEEKDAY_HOURS  = list(range(10, 20))   # 10:00 – 19:00  (Mon–Fri)
SATURDAY_HOURS = list(range(10, 15))   # 10:00 – 14:00  (Saturday)
# Sunday: CLOSED – no slots

SERVICES = [
    "Дерматолошки преглед",
    "Третмани за лице и акни",
    "Трајна епилација",
    "Третман за подмладување",
    "Филери",
    "Мезотерапија",
    "Отстранување брадавици",
    "Детски преглед",
]

SERVICE_COLORS = {
    "Дерматолошки преглед":    "clr-teal",
    "Третмани за лице и акни": "clr-rose",
    "Трајна епилација":        "clr-purple",
    "Третман за подмладување": "clr-gold",
    "Филери":                  "clr-slate",
    "Мезотерапија":            "clr-blue",
    "Отстранување брадавици":  "clr-amber",
    "Детски преглед":          "clr-green",
}

MONTHS_MK = ["", "Јануари", "Февруари", "Март", "Април", "Мај", "Јуни",
             "Јули", "Август", "Септември", "Октомври", "Ноември", "Декември"]

DAYS_SHORT_MK = ["Пон", "Вто", "Сре", "Чет", "Пет", "Саб", "Нед"]
DAYS_LONG_MK  = ["Понеделник", "Вторник", "Среда", "Четврток", "Петок", "Сабота", "Недела"]

database.init_db()


@app.context_processor
def inject_helpers():
    def service_color(service):
        return SERVICE_COLORS.get(service, "clr-slate")
    return {"service_color": service_color}


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
        flash("Погрешно корисничко име или лозинка.", "error")
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
        month_name=MONTHS_MK[month],
        day_headers=DAYS_SHORT_MK,
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

    weekday = day_date.weekday()

    # Sunday is closed
    if weekday == 6:
        return render_template("day.html",
            date_str=date_str,
            day_name=DAYS_LONG_MK[weekday],
            formatted_date=day_date.strftime("%d.%m.%Y."),
            slots=[],
            closed=True,
            year=day_date.year,
            month=day_date.month,
        )

    if weekday == 5:
        hours = SATURDAY_HOURS
    else:
        hours = WEEKDAY_HOURS

    reservations = database.get_by_date(date_str)
    booked  = {r["time"]: r for r in reservations}

    hour_times = {f"{h:02d}:00" for h in hours}

    # standard hourly slots (free or booked)
    slots = [{"time": f"{h:02d}:00", "reservation": booked.get(f"{h:02d}:00")} for h in hours]

    # squeeze in any off-hour bookings (e.g. 10:30) at the right position
    for time_str, res in booked.items():
        if time_str not in hour_times:
            slots.append({"time": time_str, "reservation": res})

    slots.sort(key=lambda s: s["time"])

    return render_template("day.html",
        date_str=date_str,
        day_name=DAYS_LONG_MK[weekday],
        formatted_date=day_date.strftime("%d.%m.%Y."),
        slots=slots,
        closed=False,
        year=day_date.year,
        month=day_date.month,
    )


# ── Client history ────────────────────────────────────────────────────────────

@app.route("/client/<path:client_name>")
@login_required
def client_history(client_name):
    reservations = database.get_by_client(client_name)
    today = date.today().isoformat()
    return render_template("client.html",
        client_name=client_name,
        reservations=reservations,
        today=today,
    )


# ── Schedule next appointment ───────────────────────────────────────────────

@app.route("/schedule_next")
@login_required
def schedule_next():
    """Compute base_date + N weeks and open the booking form pre-filled."""
    base_date = request.args.get("base_date", "")
    weeks_raw = request.args.get("weeks", "")
    new_date = base_date
    try:
        weeks = max(1, min(int(weeks_raw), 104))
        new_date = (date.fromisoformat(base_date) + timedelta(weeks=weeks)).isoformat()
    except ValueError:
        pass
    return redirect(url_for("add",
        date=new_date,
        time=request.args.get("time", ""),
        client_name=request.args.get("client_name", ""),
        phone=request.args.get("phone", ""),
        service_type=request.args.get("service_type", ""),
    ))


# ── Booking form ──────────────────────────────────────────────────────────────

@app.route("/add", methods=["GET", "POST"])
@app.route("/add/<prefill_date>/<prefill_time>", methods=["GET", "POST"])
@login_required
def add(prefill_date=None, prefill_time=None):
    if request.method == "POST":
        client_name  = request.form["client_name"].strip()
        phone        = request.form.get("phone", "").strip()
        date_        = request.form["date"]
        time_        = request.form["time"]
        service_sel  = request.form.get("service_select", "")
        service_cust = request.form.get("service_custom", "").strip()
        service_type = service_cust if service_sel == "other" else service_sel
        notes        = request.form.get("notes", "").strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Ве молиме пополнете ги сите задолжителни полиња.", "error")
            return render_template("form.html", action="Додади", services=SERVICES,
                                   prefill={"date": date_, "time": time_,
                                            "client_name": client_name, "phone": phone,
                                            "notes": notes, "service_type": service_type})
        database.add(client_name, phone, date_, time_, service_type, notes)
        flash(f"Терминот за {client_name} е закажан. ✓", "success")
        return redirect(url_for("day_view", date_str=date_))

    # support prefill via query params (used by "schedule next" buttons)
    prefill = {
        "date":         prefill_date or request.args.get("date", ""),
        "time":         prefill_time or request.args.get("time", ""),
        "client_name":  request.args.get("client_name", ""),
        "phone":        request.args.get("phone", ""),
        "service_type": request.args.get("service_type", ""),
    }
    pick_date = request.args.get("pick_date") and not prefill["date"]
    return render_template("form.html", action="Додади", services=SERVICES,
                           prefill=prefill, pick_date=pick_date)


@app.route("/edit/<int:res_id>", methods=["GET", "POST"])
@login_required
def edit(res_id):
    reservation = database.get_by_id(res_id)
    if not reservation:
        flash("Терминот не е пронајден.", "error")
        return redirect(url_for("calendar_view"))

    if request.method == "POST":
        client_name  = request.form["client_name"].strip()
        phone        = request.form.get("phone", "").strip()
        date_        = request.form["date"]
        time_        = request.form["time"]
        service_sel  = request.form.get("service_select", "")
        service_cust = request.form.get("service_custom", "").strip()
        service_type = service_cust if service_sel == "other" else service_sel
        notes        = request.form.get("notes", "").strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Ве молиме пополнете ги сите задолжителни полиња.", "error")
            return render_template("form.html", action="Измени", services=SERVICES,
                                   res_id=res_id, prefill=dict(request.form))
        database.update(res_id, client_name, phone, date_, time_, service_type, notes)
        flash(f"Терминот за {client_name} е изменет. ✓", "success")
        return redirect(url_for("day_view", date_str=date_))

    return render_template("form.html", action="Измени", services=SERVICES,
                           res_id=res_id, prefill=dict(reservation))


@app.route("/delete/<int:res_id>", methods=["POST"])
@login_required
def delete(res_id):
    res = database.get_by_id(res_id)
    back_date = res["date"] if res else None
    if res:
        database.delete(res_id)
        flash(f"Терминот за {res['client_name']} е избришан.", "success")
    if back_date:
        return redirect(url_for("day_view", date_str=back_date))
    return redirect(url_for("calendar_view"))


@app.route("/reschedule/<int:res_id>", methods=["GET", "POST"])
@login_required
def reschedule(res_id):
    reservation = database.get_by_id(res_id)
    if not reservation:
        flash("Терминот не е пронајден.", "error")
        return redirect(url_for("calendar_view"))

    if request.method == "POST":
        client_name  = request.form["client_name"].strip()
        phone        = request.form.get("phone", "").strip()
        date_        = request.form["date"]
        time_        = request.form["time"]
        service_sel  = request.form.get("service_select", "")
        service_cust = request.form.get("service_custom", "").strip()
        service_type = service_cust if service_sel == "other" else service_sel
        notes        = request.form.get("notes", "").strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Ве молиме пополнете ги сите задолжителни полиња.", "error")
            return render_template("form.html", action="Промени датум", services=SERVICES,
                                   reschedule_id=res_id, pick_date=True,
                                   prefill={"date": date_, "time": time_,
                                            "client_name": client_name, "phone": phone,
                                            "notes": notes, "service_type": service_type})

        database.add(client_name, phone, date_, time_, service_type, notes)
        database.delete(res_id)
        flash(f"Терминот за {client_name} е преместен за {date_}. ✓", "success")
        return redirect(url_for("day_view", date_str=date_))

    prefill = {
        "client_name":  reservation["client_name"],
        "phone":        reservation["phone"] or "",
        "time":         reservation["time"],
        "service_type": reservation["service_type"],
        "notes":        reservation["notes"] or "",
        "date":         "",
    }
    return render_template("form.html", action="Промени датум", services=SERVICES,
                           reschedule_id=res_id, prefill=prefill, pick_date=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5051)
