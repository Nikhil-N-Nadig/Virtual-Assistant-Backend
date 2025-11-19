
# shopmate/routes/reminder_routes.py
from flask import request, jsonify
import pytz
from shopmate import app, db
from shopmate.models import Reminder
from datetime import datetime
import traceback

import dateparser  # <-- install: pip install dateparser

IST = pytz.timezone("Asia/Kolkata")  # your local timezone


@app.route("/reminder", methods=["POST"])
def create_reminder():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    products = data.get("products")
    time_input = data.get("send_time")  # Natural language time
    note = data.get("note")

    if not user_id or not products or not time_input:
        return jsonify({"success": False, "error": "user_id, products, send_time required"}), 400

    try:
        # 1️⃣ Parse natural language time in IST
        parsed_time_local = dateparser.parse(
            time_input,
            settings={
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": True
            }
        )

        if not parsed_time_local:
            return jsonify({"success": False, "error": "Could not understand the time format"}), 400

        # 2️⃣ Convert IST → UTC
        send_time = parsed_time_local.astimezone(pytz.utc).replace(tzinfo=None)

    except Exception as e:
        print("Time parse error:", e)
        return jsonify({"success": False, "error": "Invalid time format"}), 400

    try:
        rem = Reminder(
        user_id=user_id,
        products=products,
        send_time=send_time,
        note=note
    )
        db.session.add(rem)
        db.session.commit()
        rems = Reminder.query.filter_by(user_id=user_id).order_by(Reminder.send_time.asc()).all()
        print(rems)
        out = []
        for r in rems:
            out.append({
                "id": r.id,
                "send_time": r.send_time,
                "created_at": r.created_at.isoformat(),
                "status": r.status,
                "note": r.note
            })
        print(out)
        return jsonify({"success": True, "reminder_id": rem.id}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# Get reminders for user
@app.route("/reminders/<int:user_id>", methods=["GET"])
def get_reminders(user_id):
    try:
        rems = Reminder.query.filter_by(user_id=user_id).order_by(Reminder.send_time.asc()).all()
        out = []
        for r in rems:
            out.append({
                "id": r.id,
                "products": r.products,
                "send_time": r.send_time.isoformat(),
                "created_at": r.created_at.isoformat(),
                "status": r.status,
                "note": r.note
            })
        return jsonify({"success": True, "reminders": out}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Cancel / delete a reminder
@app.route("/reminder/<int:reminder_id>", methods=["DELETE"])
def cancel_reminder(reminder_id):
    try:
        rem = Reminder.query.get_or_404(reminder_id)
        rem.status = "cancelled"
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
