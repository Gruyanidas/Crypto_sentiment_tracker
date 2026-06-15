from flask import Flask, render_template, request, redirect, url_for, flash
import database

app = Flask(__name__)
app.secret_key = "reservation-tracker-secret"

database.init_db()


@app.route("/")
def index():
    from datetime import date
    today = database.get_today()
    all_reservations = database.get_all()
    return render_template("index.html", today=today, reservations=all_reservations,
                           today_str=date.today().isoformat())


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        client_name = request.form["client_name"].strip()
        date_ = request.form["date"]
        time_ = request.form["time"]
        service_type = request.form["service_type"].strip()
        notes = request.form["notes"].strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Client name, date, time and service type are required.", "error")
            return render_template("form.html", action="Add", reservation=request.form)

        database.add(client_name, date_, time_, service_type, notes)
        flash(f"Reservation for {client_name} added.", "success")
        return redirect(url_for("index"))

    return render_template("form.html", action="Add", reservation={})


@app.route("/edit/<int:res_id>", methods=["GET", "POST"])
def edit(res_id):
    reservation = database.get_by_id(res_id)
    if not reservation:
        flash("Reservation not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        client_name = request.form["client_name"].strip()
        date_ = request.form["date"]
        time_ = request.form["time"]
        service_type = request.form["service_type"].strip()
        notes = request.form["notes"].strip()

        if not client_name or not date_ or not time_ or not service_type:
            flash("Client name, date, time and service type are required.", "error")
            return render_template("form.html", action="Edit", reservation=request.form, res_id=res_id)

        database.update(res_id, client_name, date_, time_, service_type, notes)
        flash(f"Reservation for {client_name} updated.", "success")
        return redirect(url_for("index"))

    return render_template("form.html", action="Edit", reservation=reservation, res_id=res_id)


@app.route("/delete/<int:res_id>", methods=["POST"])
def delete(res_id):
    res = database.get_by_id(res_id)
    if res:
        database.delete(res_id)
        flash(f"Reservation for {res['client_name']} deleted.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
