from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pandas as pd
import pyodbc
import math

hauling_bp = Blueprint('hauling', __name__)

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
        'DATABASE=BELAJAR_SYNAPSE;'
        'UID=belajar_synapse_user;'
        'PWD=belajarsynapse123#'
    )

@hauling_bp.route('/view/hauling', methods=['GET'])
@login_required
def view_hauling():
    try:
        conn = get_connection()
        search = request.args.get('search', '').strip()
        query = "SELECT * FROM azr.INS_HAULING"
        params = []

        # Filter hanya untuk user non-admin
        if not current_user.is_admin:
            query += " WHERE NRP = ?"
            # gunakan NRP (bukan id internal)
            params.append(current_user.get_id())

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        # Pindahkan kolom NRP ke depan (jika ada)
        if 'NRP' in df.columns:
            cols = ['NRP'] + [c for c in df.columns if c != 'NRP']
            df = df[cols]

        # Format tanggal jika ada
        if 'TANGGAL' in df.columns:
            df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce').dt.strftime('%d %b %Y')

        # Filter pencarian
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        # Kolom ACH ke float
        if 'ACH' in df.columns:
            df['ACH'] = pd.to_numeric(df['ACH'], errors='coerce').fillna(0)

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        total = len(df)
        pages = math.ceil(total / per_page)
        start_index = (page - 1) * per_page + 1 if total > 0 else 0
        end_index = min(start_index + per_page - 1, total)
        data_paginated = df.iloc[start_index - 1:end_index] if total > 0 else df

        return render_template(
            'view_hauling.html',
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
        print("[ERROR VIEW HAULING]", e)
        flash(f"Gagal mengambil data INSENTIF HAULING: {e}", "danger")
        return redirect(url_for("upload.upload"))
