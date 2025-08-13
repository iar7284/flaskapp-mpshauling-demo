from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import pandas as pd
import pyodbc
import math

absen_bp = Blueprint('view_absen_routes', __name__)

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
        'DATABASE=BELAJAR_SYNAPSE;'
        'UID=belajar_synapse_user;'
        'PWD=belajarsynapse123#'
    )

@absen_bp.route('/view/absen', methods=['GET'])
@login_required
def view_absen():
    try:
        conn = get_connection()
        search = request.args.get('search', '').strip()
        query = "SELECT * FROM azr.ABSEN"
        params = []

        # Cek kolom dulu biar filter aman
        cursor = conn.cursor()
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'ABSEN'")
        columns = [row[0] for row in cursor.fetchall()]

        if not current_user.is_admin:
            if 'NRP1' in columns and 'NRP2' in columns:
                query += " WHERE NRP = ? OR NRP1 = ? OR NRP2 = ?"
                params.extend([current_user.id, current_user.id, current_user.id])
            else:
                query += " WHERE NRP = ?"
                params.append(current_user.id)

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        # Hapus kolom PASSWORD jika ada
        if 'PASSWORD' in df.columns:
            df.drop(columns=['PASSWORD'], inplace=True)

        # Jika data kosong
        if df.empty:
            return render_template(
                'view_absen.html',
                data=[],
                headers=[],
                page=1,
                pages=1,
                request=request,
                start_index=0,
                end_index=0,
                total=0
            )

        # Gabungkan NRP1 & NRP2 jika ada
        if 'NRP1' in df.columns and 'NRP2' in df.columns:
            df['NRP'] = df[['NRP1', 'NRP2']].astype(str).apply(
                lambda x: ', '.join([v for v in x if v and v != 'nan']), axis=1
            )
            df.drop(columns=['NRP1', 'NRP2'], inplace=True)

        # Hapus kolom KODE jika ada
        if 'KODE' in df.columns:
            df.drop(columns=['KODE'], inplace=True)

        # Format tanggal
        if 'TANGGAL' in df.columns:
            df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce').dt.strftime('%d %b %Y')

        # Pencarian
        if search:
            mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
            df = df[mask]

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        total = len(df)
        pages = max(1, math.ceil(total / per_page))
        start_index = (page - 1) * per_page + 1 if total > 0 else 0
        end_index = min(start_index + per_page - 1, total)
        data_paginated = df.iloc[start_index - 1:end_index] if total > 0 else []

        return render_template(
            'view_absen.html',
            data=data_paginated.to_dict(orient='records'),
            headers=df.columns,
            page=page,
            pages=pages,
            request=request,
            start_index=start_index,
            end_index=end_index,
            total=total
        )

    except Exception as e:
        print("[ERROR VIEW ABSEN]", e)
        flash("Gagal mengambil data ABSEN", "danger")
        return redirect(url_for("upload.upload"))
