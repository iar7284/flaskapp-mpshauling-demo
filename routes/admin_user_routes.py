from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pyodbc
import traceback

admin_user_bp = Blueprint('admin_user', __name__)

# Fungsi koneksi database
def get_connection():
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
        'DATABASE=BELAJAR_SYNAPSE;'
        'UID=belajar_synapse_user;'
        'PWD=belajarsynapse123#'
    )
    return pyodbc.connect(conn_str)

# GET dan POST untuk tambah user
@admin_user_bp.route('/admin/user', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Akses hanya untuk admin.", "danger")
        return redirect(url_for('home'))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            nrp = request.form['nrp']
            nama = request.form['nama']
            tgl_lahir = request.form['tgl_lahir']
            email = request.form['email']
            is_admin = 1 if 'is_admin' in request.form else 0

            cursor.execute("""
                INSERT INTO azr.USERS (NRP, NAMA, TGL_LAHIR, EMAIL, IS_ADMIN)
                VALUES (?, ?, ?, ?, ?)
            """, (nrp, nama, tgl_lahir, email, is_admin))
            conn.commit()
            flash("User berhasil ditambahkan.", "success")
        except Exception as e:
            traceback.print_exc()
            flash(f"Gagal menambahkan user: {str(e)}", "danger")

    cursor.execute("SELECT NRP, NAMA, EMAIL, IS_ADMIN FROM azr.USERS")
    users = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

    conn.close()
    return render_template('admin_user.html', users=users)

# DELETE user
@admin_user_bp.route('/admin/user/delete/<nrp>', methods=['POST'])
@login_required
def delete_user(nrp):
    if not current_user.is_authenticated or not current_user.is_admin:
        flash("Akses hanya untuk admin.", "danger")
        return redirect(url_for('home'))

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM azr.USERS WHERE NRP = ?", (nrp,))
        conn.commit()
        conn.close()
        flash("User berhasil dihapus.", "success")
    except Exception as e:
        traceback.print_exc()
        flash(f"Gagal menghapus user: {str(e)}", "danger")

    return redirect(url_for('admin_user.manage_users'))
