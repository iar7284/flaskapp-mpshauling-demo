from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import login_required, current_user
import pandas as pd
import os
import uuid
from werkzeug.utils import secure_filename
from db import get_connection

revisi_bp = Blueprint("revisi", __name__)

# ================== KONFIGURASI ==================
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'lampiran_revisi')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_image(filename):
    return filename.lower().endswith(('jpg', 'jpeg', 'png'))

def is_pdf(filename):
    return filename.lower().endswith('pdf')

# ================== FORM PENGAJUAN ==================
@revisi_bp.route("/revisi", methods=["GET", "POST"])
@login_required
def revisi_form():
    if request.method == "POST":
        nrp = current_user.nrp
        kategori = request.form.get("kategori")

        area_kerja = ""
        detail_revisi = ""
        keterangan = ""
        km_awal = km_akhir = hm_awal = hm_akhir = ritasi = None
        lampiran_filename = None

        if kategori == "ABSEN":
            area_kerja = request.form.get("area_kerja")
            revisi_absen = request.form.getlist("revisi_absen[]")
            detail_revisi = ", ".join(revisi_absen)
            keterangan = request.form.get("keterangan_absen")

        elif kategori == "HM":
            revisi_hm = request.form.getlist("revisi_hm[]")
            detail_revisi = ", ".join(revisi_hm)
            km_awal = request.form.get("km_awal")
            km_akhir = request.form.get("km_akhir")
            hm_awal = request.form.get("hm_awal")
            hm_akhir = request.form.get("hm_akhir")
            ritasi = request.form.get("ritasi")
            keterangan = request.form.get("keterangan_hm")

        # ========== Upload File (WAJIB) ==========
        file = request.files.get('lampiran')
        if not file or file.filename == '':
            flash("Lampiran revisi wajib diunggah.", "danger")
            return redirect(request.url)

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, unique_name)
            file.save(file_path)
            lampiran_filename = unique_name
        else:
            flash("Format file tidak diizinkan. Hanya PDF atau gambar (jpg, png).", "danger")
            return redirect(request.url)

        # ========== Simpan Ke Database ==========
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO azr.REVISI_REQUEST (
                    NRP, KATEGORI, AREA_KERJA, DETAIL_REVISI, KETERANGAN,
                    KM_AWAL, KM_AKHIR, HM_AWAL, HM_AKHIR, RITASI,
                    LAMPIRAN_FILE, STATUS, CREATED_AT
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', GETDATE())
            """, (
                nrp, kategori, area_kerja, detail_revisi, keterangan,
                km_awal, km_akhir, hm_awal, hm_akhir, ritasi, lampiran_filename
            ))
            conn.commit()
            flash("Pengajuan revisi berhasil dikirim.", "success")
        except Exception as e:
            flash(f"Gagal menyimpan revisi: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for("main.index"))

    return render_template("revisi_form.html")

# ================== HALAMAN ADMIN ==================
@revisi_bp.route("/admin/revisi")
@login_required
def admin_revisi_list():
    if not getattr(current_user, 'is_admin', False):
        flash("Akses ditolak. Anda bukan admin.", "danger")
        return redirect(url_for("main.index"))

    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM azr.REVISI_REQUEST ORDER BY CREATED_AT DESC", conn)

        # Tambahkan flag IS_EDITED untuk HM (hanya aktif jika ada data isian)
        df['IS_EDITED'] = df.apply(
            lambda x: any([x['KM_AWAL'], x['KM_AKHIR'], x['HM_AWAL'], x['HM_AKHIR'], x['RITASI']]) if x['KATEGORI'] == 'HM' else True,
            axis=1
        )

        revisi_list = df.to_dict(orient="records")
        has_new_revisi = any(item["STATUS"] == "Pending" for item in revisi_list)

        for item in revisi_list:
            filename = item.get('LAMPIRAN_FILE')
            item['IS_IMAGE'] = is_image(filename) if filename else False
            item['IS_PDF'] = is_pdf(filename) if filename else False

    except Exception as e:
        flash(f"Gagal mengambil data: {e}", "danger")
        revisi_list = []
        has_new_revisi = False
    finally:
        conn.close()

    return render_template("admin_revisi_list.html", revisi_list=revisi_list, has_new_revisi=has_new_revisi)

# ================== EDIT REVISI (ADMIN) ==================
@revisi_bp.route("/admin/revisi/edit/<int:revisi_id>", methods=["GET", "POST"])
@login_required
def edit_revisi(revisi_id):
    if not getattr(current_user, 'is_admin', False):
        flash("Akses ditolak. Anda bukan admin.", "danger")
        return redirect(url_for("main.index"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            kategori = request.form.get("kategori")
            area_kerja = request.form.get("area_kerja")
            detail_revisi = request.form.get("detail_revisi")
            keterangan = request.form.get("keterangan")
            km_awal = request.form.get("km_awal")
            km_akhir = request.form.get("km_akhir")
            hm_awal = request.form.get("hm_awal")
            hm_akhir = request.form.get("hm_akhir")
            ritasi = request.form.get("ritasi")

            # Ambil NRP untuk update tabel utama
            cursor.execute("SELECT NRP FROM azr.REVISI_REQUEST WHERE ID=?", (revisi_id,))
            user_nrp = cursor.fetchone()[0]

            # Update revisi + set status Done
            cursor.execute("""
                UPDATE azr.REVISI_REQUEST 
                SET KATEGORI=?, AREA_KERJA=?, DETAIL_REVISI=?, KETERANGAN=?,
                    KM_AWAL=?, KM_AKHIR=?, HM_AWAL=?, HM_AKHIR=?, RITASI=?, STATUS='Done'
                WHERE ID=?
            """, (kategori, area_kerja, detail_revisi, keterangan,
                  km_awal, km_akhir, hm_awal, hm_akhir, ritasi, revisi_id))

            # Update tabel utama sesuai kategori
            if kategori == "ABSEN":
                cursor.execute("""
                    UPDATE azr.ABSEN_TABLE
                    SET AREA_KERJA=?, KETERANGAN=?
                    WHERE NRP=?
                """, (area_kerja, keterangan, user_nrp))
            elif kategori == "HM":
                cursor.execute("""
                    UPDATE azr.HM_TABLE
                    SET KM_AWAL=?, KM_AKHIR=?, HM_AWAL=?, HM_AKHIR=?, RITASI=?
                    WHERE NRP=?
                """, (km_awal, km_akhir, hm_awal, hm_akhir, ritasi, user_nrp))

            conn.commit()
            flash("Data revisi & data user berhasil diperbarui (status otomatis Done).", "success")
            return redirect(url_for("revisi.admin_revisi_list"))
        except Exception as e:
            flash(f"Gagal mengupdate revisi: {e}", "danger")
        finally:
            conn.close()

    cursor.execute("SELECT * FROM azr.REVISI_REQUEST WHERE ID=?", (revisi_id,))
    revisi_data = cursor.fetchone()
    conn.close()

    return render_template("edit_revisi.html", revisi=revisi_data)

# ================== PREVIEW LAMPIRAN ==================
@revisi_bp.route("/lampiran_revisi/<filename>")
@login_required
def preview_lampiran(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        flash("File lampiran tidak ditemukan.", "danger")
        return redirect(url_for("revisi.admin_revisi_list"))

# ================== UPDATE STATUS REVISI ==================
@revisi_bp.route("/admin/revisi/update/<int:revisi_id>", methods=["POST"])
@login_required
def update_revisi_status(revisi_id):
    if not getattr(current_user, 'is_admin', False):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Ambil data revisi dulu
        cursor.execute("""
            SELECT STATUS, KATEGORI, KM_AWAL, KM_AKHIR, HM_AWAL, HM_AKHIR, RITASI 
            FROM azr.REVISI_REQUEST 
            WHERE ID = ?
        """, (revisi_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Revisi tidak ditemukan"}), 404

        status, kategori, km_awal, km_akhir, hm_awal, hm_akhir, ritasi = row

        # Cegah update jika sudah Done
        if status == "Done":
            return jsonify({"error": "Revisi ini sudah ditandai Done."}), 400

        # Validasi khusus HM: harus sudah ada isian
        if kategori == "HM":
            if not any([km_awal, km_akhir, hm_awal, hm_akhir, ritasi]):
                return jsonify({"error": "Revisi HM harus di-edit dulu sebelum ditandai Done"}), 400

        # Update status jadi Done
        cursor.execute("UPDATE azr.REVISI_REQUEST SET STATUS = 'Done' WHERE ID = ?", (revisi_id,))
        conn.commit()

        return jsonify({"message": "Status berhasil diperbarui ke Done."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
