# routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from datetime import datetime, timedelta
import random, smtplib
from email.mime.text import MIMEText
from db import get_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ==================== Class User ====================
class User(UserMixin):
    def _init_(self, nrp, nama, is_admin):
        self.id = nrp  # id untuk Flask-Login
        self.nrp = nrp
        self.nama = nama
        self.is_admin = is_admin


# ==================== Loader ====================
def load_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT NRP, NAMA, IS_ADMIN FROM azr.USERS WHERE NRP = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user = User(nrp=row[0], nama=row[1], is_admin=bool(row[2]))
        return user
    return None


# ==================== Kirim Email OTP ====================
def send_email_otp(recipient_email, otp):
    try:
        sender_email = 'zyiel.418@gmail.com'
        sender_password = 'zato gtew zrby czxh'  # App Password Gmail
        subject = 'Kode OTP Login - Aplikasi MPS'
        body = f'Kode OTP Anda adalah: {otp}\nBerlaku selama 24 jam.'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"[ERROR] Gagal kirim OTP: {e}")

# ==================== Login ====================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login & belum logout ? langsung ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        nrp = request.form['nrp'].strip().upper()
        tgl_lahir = request.form['tanggal_lahir'].strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT NRP, EMAIL, IS_ADMIN, OTP, OTP_EXPIRED_AT FROM azr.USERS
            WHERE NRP = ? AND CONVERT(VARCHAR, TGL_LAHIR, 23) = ?
        """, (nrp, tgl_lahir))
        user = cursor.fetchone()

        if not user:
            flash("NRP atau Tanggal Lahir salah.", "danger")
            conn.close()
            return redirect(url_for('auth.login'))

        email, is_admin, otp_existing, otp_expired_at = user[1], bool(user[2]), user[3], user[4]

        otp = None
        expired_at = None

        # Jika OTP lama masih berlaku ? pakai OTP lama
        if otp_existing and otp_expired_at and datetime.utcnow() < otp_expired_at:
            otp = otp_existing
            print(f"[DEBUG] OTP lama masih berlaku untuk {nrp}: {otp}")
        else:
            # Jika expired atau belum ada ? buat OTP baru
            otp = str(random.randint(100000, 999999))
            expired_at = datetime.utcnow() + timedelta(hours=24)
            cursor.execute("""
                UPDATE azr.USERS
                SET OTP = ?, OTP_EXPIRED_AT = ?
                WHERE NRP = ?
            """, (otp, expired_at, nrp))
            cursor.execute("""
                INSERT INTO azr.OTP_LOGS (NRP, OTP, STATUS)
                VALUES (?, ?, 'Generated')
            """, (nrp, otp))
            conn.commit()
            send_email_otp(email, otp)
            print(f"[DEBUG] OTP baru untuk {nrp}: {otp}")

        conn.close()
        session['pending_nrp'] = nrp
        flash("Kode OTP telah dikirim ke email Anda (atau gunakan OTP lama jika masih berlaku).", "info")
        return redirect(url_for('auth.verify_otp'))

    return render_template('login.html')

# ==================== Verifikasi OTP ====================
@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_nrp' not in session:
        flash("Session tidak ditemukan. Silakan login ulang.", "danger")
        return redirect(url_for('auth.login'))

    nrp = session['pending_nrp']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT OTP, OTP_EXPIRED_AT, IS_ADMIN
        FROM azr.USERS
        WHERE NRP = ?
    """, (nrp,))
    result = cursor.fetchone()

    if not result:
        flash("Data user tidak ditemukan.", "danger")
        conn.close()
        return redirect(url_for('auth.login'))

    otp_db, expired_at, is_admin = result

    if not otp_db or datetime.utcnow() > expired_at:
        cursor.execute("""
            UPDATE azr.OTP_LOGS
            SET STATUS='Expired'
            WHERE NRP=? AND OTP=? AND STATUS='Generated'
        """, (nrp, otp_db))
        conn.commit()
        conn.close()
        flash("Kode OTP kadaluarsa. Silakan login ulang.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        input_otp = request.form['otp'].strip()
        if input_otp == otp_db:
            # Jika OTP benar, login & jangan hapus OTP (biar bisa dipakai sampai expired)
            cursor.execute("""
                UPDATE azr.OTP_LOGS
                SET STATUS='Verified', VERIFIED_AT=GETDATE()
                WHERE NRP=? AND OTP=? AND STATUS='Generated'
            """, (nrp, otp_db))
            conn.commit()
            conn.close()

            login_user(User(nrp, bool(is_admin)))
            session.pop('pending_nrp', None)

            return redirect(url_for('main.index'))
        else:
            flash("OTP salah.", "danger")

    conn.close()
    return render_template('verify_otp.html', nrp=nrp)

# ==================== Logout ====================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for('auth.login'))
