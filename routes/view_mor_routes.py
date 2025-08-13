from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import pandas as pd
import pyodbc
import math
import traceback

mor_bp = Blueprint('mor', __name__)

@mor_bp.route('/view/mor', methods=['GET'])
@login_required
def view_mor():
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
            'DATABASE=BELAJAR_SYNAPSE;'
            'UID=belajar_synapse_user;'
            'PWD=belajarsynapse123#'
        )
        search = request.args.get('search', '').strip()

        # Admin: lihat semua data. User biasa: filter per NRP.
        if current_user.is_admin:
            query = "SELECT * FROM azr.INS_MOR"
            params = []
        else:
            query = "SELECT * FROM azr.INS_MOR WHERE NRP = ?"
            params = [current_user.get_id()]

        df = pd.read_sql(query, conn, params=params)
        conn.close()

        # Format tanggal jika ada
        date_columns = ['Join date', 'Last Promote']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d %b %Y')

        # Filter pencarian
        if search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        total = len(df)
        pages = math.ceil(total / per_page)
        start_index = (page - 1) * per_page + 1 if total > 0 else 0
        end_index = min(start_index + per_page - 1, total)
        data_paginated = df.iloc[start_index - 1:end_index] if total > 0 else df

        return render_template(
            'view_mor.html',
            data=data_paginated.to_dict(orient='records'),
            headers=df.columns,
            page=page,
            pages=pages,
            request=request,
            start_index=start_index,
            end_index=end_index,
            total=total
        )

    except Exception:
        print(traceback.format_exc())
        flash("Gagal mengambil data MOR.", "danger")
        return redirect(url_for('main.index'))
