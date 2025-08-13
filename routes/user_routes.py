from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, UserMixin
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText

user_bp = Blueprint('user', __name__)

# Dummy database sementara
USER_DB = {
    'ADMIN1': {'tanggal_lahir': '2004-06-17', 'email': 'zyiel.418@gmail.com', 'is_admin': True},
    '17452599': {'tanggal_lahir': '2004-06-25', 'email': 'gorell1745@gmail.com', 'is_admin': False}
}
OTP_SESSIONS = {}

class User(UserMixin):
    def __init__(self, nrp, is_admin):
        self.id = nrp               # Wajib untuk Flask-Login
        self.nrp = nrp              # Diperlukan untuk akses current_user.nrp
        self.is_admin = is_admin   # Menentukan role login

@user_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nrp = request.form['nrp'].strip().upper()
        tgl_lahir = request.form['tanggal_lahir'].strip()
        user = USER_DB.get(nrp)

        if not user or user['tanggal_lahir'] != tgl_lahir:
            flash("NRP atau Tanggal Lahir salah.", "danger")
            return redirect(url_for('user.login'))

        # Generate OTP dan simpan ke session
        otp = str(random.randint(100000, 999999))
        OTP_SESSIONS[nrp] = otp
        send_email_otp(user['email'], otp)

        session['pending_nrp'] = nrp
        session['otp_expire'] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        flash("Kode OTP telah dikirim ke email Anda.", "info")
        return redirect(url_for('user.verify_otp'))

    return render_template('login.html')

@user_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_nrp' not in session or 'otp_expire' not in session:
        flash("Session OTP tidak ditemukan. Silakan login ulang.", "danger")
        return redirect(url_for('user.login'))

    nrp = session['pending_nrp']
    otp_expire = datetime.fromisoformat(session['otp_expire'])

    if datetime.utcnow() > otp_expire:
        flash("Kode OTP kadaluarsa. Silakan login ulang.", "danger")
        session.pop('pending_nrp', None)
        session.pop('otp_expire', None)
        OTP_SESSIONS.pop(nrp, None)
        return redirect(url_for('user.login'))

    if request.method == 'POST':
        input_otp = request.form['otp'].strip()
        if OTP_SESSIONS.get(nrp) == input_otp:
            user = USER_DB[nrp]
            login_user(User(nrp, user['is_admin']))
            session['is_admin'] = user['is_admin']
            session.pop('pending_nrp', None)
            session.pop('otp_expire', None)
            OTP_SESSIONS.pop(nrp, None)
            return redirect(url_for('user.index'))
        else:
            flash("OTP salah.", "danger")

    return render_template('verify_otp.html', nrp=nrp)

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Anda telah logout.", "info")
    return redirect(url_for('user.login'))

def send_email_otp(recipient_email, otp):
    try:
        sender_email = 'zyiel.418@gmail.com'
        sender_password = 'zato gtew zrby czxh'
        subject = 'Kode OTP Login - Aplikasi MPS'
        body = f'Kode OTP Anda adalah: {otp}\nBerlaku selama 5 menit. Jangan bagikan ke siapa pun.'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()

        print(f"[INFO] OTP dikirim ke {recipient_email}")
    except Exception as e:
        print(f"[ERROR] Gagal mengirim email OTP: {e}")
