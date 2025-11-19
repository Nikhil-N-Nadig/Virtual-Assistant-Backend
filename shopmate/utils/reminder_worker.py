# shopmate/utils/reminder_worker.py
import os
import traceback
from email.mime.text import MIMEText
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from shopmate import app, db, Mail
from flask_mail import Message as MailMessage
from shopmate.models import Reminder, User

mail = Mail(app)



CHECK_INTERVAL_SECONDS = int(os.getenv("REMINDER_CHECK_INTERVAL", "6000"))


# -------------------------------------------------------------------
# Build HTML email body
# -------------------------------------------------------------------
def build_reminder_email_html(user_name, products, product_time_str, base_url=None):
    product_cards_html = ""
    for p in products:
        title = p.get("title", "Product")
        price = p.get("price", "N/A")
        link = p.get("link", "#")
        thumb = p.get("image") or p.get("thumbnail") or ""

        img_tag = (
            f'<img src="{thumb}" style="width:120px;height:80px;object-fit:contain;border-radius:8px;" />'
            if thumb else ""
        )

        product_cards_html += f"""
        <tr style="background:#fff;margin-bottom:12px;border-radius:8px;">
            <td style="padding:12px;vertical-align:top;">{img_tag}</td>
            <td style="padding:12px;vertical-align:top;">
                <div style="font-weight:600;color:#111">{title}</div>
                <div style="color:#666;margin-top:6px;">Price: <strong>{price}</strong></div>
                <div style="margin-top:8px;">
                    <a href="{link}" style="color:#5B21B6;text-decoration:none;">View product →</a>
                </div>
            </td>
        </tr>
        """

    html = f"""
    <html>
      <body style="background:#f4f6fb;padding:24px;font-family:Arial;">
        <div style="max-width:700px;margin:auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
          <h2 style="margin:0;color:#111;">Reminder — Products You Viewed</h2>
          <p style="color:#444;">Hi {user_name}, here's a reminder of products you checked on {product_time_str}.</p>

          <table style="width:100%;border-collapse:separate;border-spacing:12px 12px;">
            {product_cards_html}
          </table>

          <p style="color:#333;margin-top:16px;">Would you like to checkout any of these?</p>

          <a href="{base_url or '#'}"
             style="display:inline-block;background:#5B21B6;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;margin-top:12px;">
             Open ShopMate
          </a>
        </div>
      </body>
    </html>
    """

    return html


# -------------------------------------------------------------------
# NEW — Send email using Flask-Mail (same as OTP mails)
# -------------------------------------------------------------------
def send_email(to_email, subject, html_body):
    try:
        print("calling send mail")
        msg = MailMessage(
            subject=subject,
            sender=app.config["MAIL_USERNAME"],
            recipients=[to_email]
        )
        msg.body = "This email contains HTML content. Please enable HTML mode to view."
        msg.html = html_body

        mail.send(msg)
        print ("Mail sent",msg)
        return True, None

    except Exception as e:
        print("Reminder email failed:", e)
        return False, str(e)


# -------------------------------------------------------------------
# Find user email + name
# -------------------------------------------------------------------
def find_user_email(user_id):
    user = User.query.get(user_id)
    if not user:
        return None, None
    return user.email, user.name or user.username


# -------------------------------------------------------------------
# Process + send pending reminders
# -------------------------------------------------------------------
def process_pending_reminders():
    with app.app_context():
        now = datetime.utcnow()
        pending = Reminder.query.filter(
            Reminder.status == "pending",
        ).all()
        

        print("Now UTC:", now)


        print("Pending:-",pending);

        for rem in pending:
            try:
                to_email, user_name = find_user_email(rem.user_id)
                if not to_email:
                    rem.status = "failed"
                    db.session.commit()
                    continue

                html = build_reminder_email_html(
                    user_name=user_name,
                    products=rem.products,
                    product_time_str=rem.created_at.strftime("%b %d, %Y %H:%M UTC"),
                    base_url=os.getenv("FRONTEND_URL")
                )

                ok, err = send_email(
                    to_email,
                    f"Still looking at these {len(rem.products)} product(s)?",
                    html
                )

                rem.status = "sent" if ok else "failed"
                db.session.commit()

            except Exception as e:
                print("Reminder error:", e)
                traceback.print_exc()
                rem.status = "failed"
                db.session.commit()


# -------------------------------------------------------------------
# Start scheduler
# -------------------------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(
    process_pending_reminders,
    "interval",
    seconds=CHECK_INTERVAL_SECONDS,
    id="reminder_check",
    replace_existing=True
)

def start_scheduler():
    try:
        if not scheduler.running:
            scheduler.start()
            print("Reminder scheduler started.")
    except Exception as e:
        print("Scheduler start error:", e)
