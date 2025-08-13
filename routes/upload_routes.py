import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from excel_parser import bulk_insert_data

upload_bp = Blueprint('upload', __name__)

# Lokasi folder upload
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'upload'))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Kategori yang valid
VALID_CATEGORIES = ['hm', 'absen', 'hauling', 'rom', 'mor']

@upload_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if not current_user.is_admin:
        flash("Anda tidak memiliki akses untuk upload data.", "danger")
        return redirect(url_for("main.index"))

    if request.method == 'POST':
        file = request.files.get('excel_file')
        category = request.form.get("category", "").lower().strip()

        # Validasi input
        if not file or file.filename.strip() == '' or not category:
            flash('File dan kategori wajib diisi.', 'warning')
            return redirect(request.url)

        if category not in VALID_CATEGORIES:
            flash('Kategori tidak valid.', 'danger')
            return redirect(request.url)

        try:
            # Simpan file ke folder upload
            filename = file.filename.replace(" ", "_")
            filepath = os.path.join(UPLOAD_DIR, filename)
            file.save(filepath)

            # Proses parsing & insert dengan validasi duplikat
            result = bulk_insert_data(filepath, category)
            if result['status'] == 'failed':
                flash(result['message'], "danger")
            else:
                if result['inserted'] == 0:
                    flash("Upload berhasil. File hanya berisi header, tidak ada data yang dimasukkan.", "info")
                else:
                    flash(f"Upload berhasil. Total baris dimasukkan: {result['inserted']}", "success")

            return redirect(url_for("upload.upload"))

        except Exception as e:
            flash(f"Terjadi kesalahan saat upload: {str(e)}", "danger")
            return redirect(request.url)

    return render_template('upload.html')


@upload_bp.route('/download_template/<category>')
@login_required
def download_template(category):
    category = category.lower()
    filename_map = {
        'hm': 'template_hm.xlsx',
        'absen': 'template_absen.xlsx',
        'hauling': 'template_hauling.xlsx',
        'rom': 'template_rom.xlsx',
        'mor': 'template_mor.xlsx'
    }

    filename = filename_map.get(category)
    if not filename:
        flash("Kategori template tidak dikenal.", "warning")
        return redirect(url_for('upload.upload'))

    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        flash(f"Template tidak ditemukan: {filename}", "danger")
        return redirect(url_for('upload.upload'))

    return send_file(filepath,
                     as_attachment=True,
                     download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
