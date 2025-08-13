import pandas as pd
import pyodbc
import os
from datetime import datetime

# Struktur tabel per kategori
TABLE_MAP = {
    'hm': {
        'table': 'azr.HM',
        'columns': ['NRP', 'NAMA', 'PERIODE', 'TANGGAL', 'SHIFT', 'UNIT',
                    'HM AWAL', 'HM AKHIR', 'RIT', 'HM', 'INSENTIF', 'KET',
                    'TOT RIT', 'TOT HM', 'TOT INSENTIF']  # R & PASSWORD dihapus
    },
    'absen': {
        'table': 'azr.ABSEN',
        'columns': ['NRP', 'NAMA', 'PERIODE', 'JABATAN', 'TANGGAL', 'SHIFT', 'HR', 'JAM',
                    'SPL', 'UU', 'LBR', '1.5', '2', '3', '4', 'TOT', 'ULAP', 'DEPT', 'KTR',
                    'STATUS', 'KTR SHIFT', 'FINGER IN', 'FINGER OUT', 'AREA KERJA',
                    'TOT SPL', 'TOT LEMBURAN', 'TOT ULAP', 'PASSWORD']
    },
    'hauling': {
        'table': 'azr.INS_HAULING',
        'columns': ['NRP', 'NAMA', 'PERIODE', 'TANGGAL', 'SHIFT', 'CODE UNIT',
                    'RITASE', 'ACH', 'PLAN', 'ACT', 'KET',
                    'TOT PARKIR DIJALUR', 'TOT PARKIR PREMATUR', 'TOT PARKIR PREMATUR & DIJALUR']  # TGL LAHIR dihapus
    },
    'rom': {
        'table': 'azr.INS_ROM',
        'columns': ['NRP', 'NAMA', 'PERIODE', 'TANGGAL', 'SHIFT', 'CODE UNIT',
                    'ACH', 'PLAN', 'ACT', 'KET', 'TOT GOOD', 'TOT DEFICENT']  # TGL LAHIR dihapus
    },
    'mor': {
        'table': 'azr.INS_MOR',
        'columns': [
            'NRP', 'NAMA', 'Periode', 'Jobsite', 'Posisi', 'Grade', 'Section',
            'Status Karyawan', 'Join date', 'Last Promote', 'Masa Kerja',
            'Skill A1', 'Skill A2', 'Attitude B1', 'Attitude B2',
            'Safety C1', 'Safety C2', 'Performance', 'Poin MOR',
            'HM MTD', 'HM YTD', 'HM ACC', 'Sakit', 'Ijin', 'Alpa', 'Remaks'
        ]
    }
}

# Kolom kunci untuk validasi duplikat
KEY_MAP = {
    'hm': ['NRP', 'PERIODE', 'TANGGAL'],
    'absen': ['NRP', 'TANGGAL'],
    'hauling': ['NRP', 'PERIODE', 'TANGGAL', 'CODE UNIT'],
    'rom': ['NRP', 'PERIODE', 'TANGGAL', 'CODE UNIT'],
    'mor': ['NRP', 'Periode']
}

RENAME_COLS = {
    'CODE UNIT': 'CODE_UNIT',
    'TGL LAHIR': 'TGL_LAHIR',
    'KTR SHIFT': 'KTR_SHIFT',
    'TOT LEMBUR': 'TOT LEMBURAN'
}

MAX_FLOAT = 1e38

# Mapping tipe data khusus MOR
MOR_TYPE_MAPPING = {
    'Periode': str, 'Jobsite': str, 'Nama': str, 'Posisi': str, 'NRP': str,
    'Grade': str, 'Section': str, 'Status Karyawan': str,
    'Join date': 'date', 'Last Promote': 'date',
    'Masa Kerja': float, 'Skill A1': int, 'Skill A2': int, 'Attitude B1': int, 'Attitude B2': int,
    'Safety C1': int, 'Safety C2': int,
    'Performance': float, 'Poin MOR': float,
    'HM MTD': float, 'HM YTD': float, 'HM ACC': float,
    'Sakit': int, 'Ijin': int, 'Alpa': int,
    'Remaks': str
}

def parse_tanggal_safe(val):
    try:
        dt = pd.to_datetime(val, errors='coerce')
        return dt.date() if not pd.isna(dt) else None
    except:
        return None

def normalize_nrp(nrp):
    if pd.isna(nrp): return None
    try:
        nrp_str = str(nrp).strip()
        if nrp_str.endswith(".0"):
            nrp_str = nrp_str.replace(".0", "")
        return nrp_str.zfill(8)
    except:
        return None

def convert_value(value, target_type):
    try:
        if pd.isna(value) or value == '':
            return None
        if target_type == str:
            return str(value).strip()
        elif target_type == int:
            return int(float(value))
        elif target_type == float:
            return float(value)
        elif target_type == 'date':
            dt = pd.to_datetime(value, errors='coerce')
            return dt.date() if not pd.isna(dt) else None
    except:
        return None

def bulk_insert_data(file_path, category):
    category = category.strip().lower()
    if category not in TABLE_MAP:
        raise ValueError("Kategori tidak valid.")

    config = TABLE_MAP[category]
    table = config['table']
    expected_columns = config['columns']
    key_cols = KEY_MAP.get(category, [])

    # Baca Excel
    df = pd.read_excel(file_path, dtype=str)
    df.columns = df.columns.str.strip()
    df.rename(columns=RENAME_COLS, inplace=True)

    # Gabungkan NRP1 + NRP2 jadi NRP untuk hauling & rom
    if category in ['hauling', 'rom']:
        if 'NRP1' in df.columns and 'NRP2' in df.columns:
            df['NRP'] = (df['NRP1'].fillna('') + df['NRP2'].fillna('')).apply(lambda x: x.strip() if x.strip() else None)
            df.drop(columns=['NRP1', 'NRP2'], inplace=True, errors='ignore')

    # Hapus kolom KODE jika ada
    if 'KODE' in df.columns:
        df.drop(columns=['KODE'], inplace=True, errors='ignore')

    # Pastikan semua kolom expected ada
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None
    df = df[expected_columns].copy()

    # Urutkan kolom (NRP, NAMA, PERIODE di depan)
    wanted = ['NRP', 'NAMA', 'PERIODE']
    col_map = {c.upper(): c for c in df.columns}
    front_cols = [col_map[w] for w in wanted if w in col_map]
    other_cols = [c for c in df.columns if c not in front_cols]
    df = df[front_cols + other_cols]

    # Drop baris tanpa NRP
    if 'NRP' in df.columns:
        df = df[df['NRP'].notna()]

    # Konversi tipe data
    if category == 'mor':
        for col in df.columns:
            target_type = MOR_TYPE_MAPPING.get(col)
            if target_type:
                df[col] = df[col].apply(lambda x: convert_value(x, target_type))
    else:
        for col in df.columns:
            if 'TANGGAL' in col.upper() or 'DATE' in col.upper():
                df[col] = df[col].apply(parse_tanggal_safe)
            elif 'NRP' in col.upper():
                df[col] = df[col].apply(normalize_nrp)
            else:
                df[col] = df[col].fillna('').astype(str).str.strip()

    # Semua selain date jadi string
    for col in df.columns:
        if not ('TANGGAL' in col.upper() or 'DATE' in col.upper()):
            df[col] = df[col].apply(lambda x: str(x) if x is not None else None)

    df = df.dropna(how='all')
    df = df.where(pd.notnull(df), None)

    # --- Tambahan: Jika setelah proses ini df kosong (hanya header) ---
    if df.empty:
        return {
            "status": "success",
            "inserted": 0,
            "message": "File hanya berisi header, tidak ada data untuk disimpan."
        }

    # Koneksi DB
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sqlmisis-test.public.ca87cd4bc197.database.windows.net,3342;'
        'DATABASE=BELAJAR_SYNAPSE;'
        'UID=belajar_synapse_user;'
        'PWD=belajarsynapse123#'
    )
    cursor = conn.cursor()

    # --- Cek data existing ---
    keys_str = " AND ".join([f"[{col}]" + " = ?" for col in key_cols])

    # Hapus data lama (replace)
    for _, row in df.iterrows():
        key_values = [row[col] for col in key_cols]
        delete_query = f"DELETE FROM {table} WHERE {keys_str}"
        cursor.execute(delete_query, key_values)

    # --- Insert data baru ---
    columns_str = ', '.join(f"[{col}]" for col in df.columns)
    placeholders = ', '.join(['?'] * len(df.columns))
    insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"

    cursor.fast_executemany = True
    cursor.executemany(insert_query, df.values.tolist())
    conn.commit()
    conn.close()

    return {"status": "success", "inserted": len(df)}
