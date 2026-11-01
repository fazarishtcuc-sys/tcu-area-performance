from io import BytesIO
from datetime import datetime
import pandas as pd


def load_master_data(uploaded_file):
    """
    Membaca Master Data dari file Excel yang di-upload.
    Tidak menggunakan database atau penyimpanan permanen.
    """

    if uploaded_file is None:
        raise ValueError("Silakan upload file Master Data terlebih dahulu.")

    file_bytes = uploaded_file.getvalue()

    if not file_bytes:
        raise ValueError("File Excel kosong.")

    df = pd.read_excel(
        BytesIO(file_bytes),
        engine="openpyxl"
    )

    if df.empty:
        raise ValueError("Master Data tidak memiliki baris data.")

    # Membersihkan spasi pada nama kolom
    df.columns = df.columns.astype(str).str.strip()

    # Memastikan tidak ada nama kolom kosong
    if any(col == "" for col in df.columns):
        raise ValueError("Terdapat nama kolom yang kosong.")

    return df


def get_sync_time():
    """
    Mengambil waktu terakhir data berhasil dimuat.
    """

    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")
