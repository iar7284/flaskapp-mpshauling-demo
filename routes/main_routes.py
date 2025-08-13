from flask import Blueprint, render_template
from flask_login import login_required
from db import get_connection  # pastikan ini ada

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    # Hitung revisi pending
    pending_revisi_count = 0
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM azr.REVISI_REQUEST WHERE STATUS = 'Pending'")
        pending_revisi_count = cursor.fetchone()[0]
    except Exception:
        pending_revisi_count = 0
    finally:
        conn.close()

    return render_template('index.html', pending_revisi_count=pending_revisi_count)
