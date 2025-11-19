from tasks.celery_tasks import check_price_alert
def schedule_price_alert(alert_id):
    # periodic check — schedule every hour (example)
    check_price_alert.apply_async(args=[alert_id], countdown=60*60)
