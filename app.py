import streamlit as st
import pandas as pd

from modules.data_source import (
    load_master_data,
    get_sync_time
)

# Konfigurasi halaman harus paling awal
st.set_page_config(
    page_title="TCU Area Performance",
    page_icon="📊",
    layout="wide"
)

# Judul dashboard
st.title("TCU Area Performance")
st.caption("Training Performance Analytics Dashboard")

# Inisialisasi session state
if "master_df" not in st.session_state:
    st.session_state.master_df = None

if "sync_time" not in st.session_state:
    st.session_state.sync_time = None

# Sidebar
st.sidebar.header("Data Control")

uploaded_file = st.sidebar.file_uploader(
    "Upload Master Data",
    type=["xlsx"],
    key="master_upload"
)

# Tombol refresh
if st.sidebar.button("Refresh Master Data"):
    st.session_state.master_df = None
    st.session_state.sync_time = None
    st.rerun()

# Proses upload
if uploaded_file is not None:

    try:
        with st.spinner("Membaca Master Data..."):

            df = load_master_data(uploaded_file)

            st.session_state.master_df = df
            st.session_state.sync_time = get_sync_time()

        st.sidebar.success("Master Data berhasil dimuat.")

    except Exception as e:
        st.error("Gagal membaca Master Data.")
        st.exception(e)

# Menampilkan dashboard
df = st.session_state.master_df

if df is not None:

    
    # ==========================================
    # PERSIAPAN DATA
    # ==========================================

    df_master = df.copy()

    # ==========================================
    # FILTER RENTANG WAKTU
    # ==========================================

    st.subheader("Filter Periode")

    date_column = "Event Date Start"

    if date_column in df_master.columns:

        df_master[date_column] = pd.to_datetime(
            df_master[date_column],
            errors="coerce",
            dayfirst=True
        )

        min_date = df_master[date_column].min()
        max_date = df_master[date_column].max()

        col_date1, col_date2 = st.columns(2)

        with col_date1:
            start_date = st.date_input(
                "Tanggal Mulai",
                value=min_date.date() if pd.notna(min_date) else None,
                min_value=min_date.date() if pd.notna(min_date) else None,
                max_value=max_date.date() if pd.notna(max_date) else None,
                format="DD/MM/YYYY"
            )

        with col_date2:
            end_date = st.date_input(
                "Tanggal Akhir",
                value=max_date.date() if pd.notna(max_date) else None,
                min_value=min_date.date() if pd.notna(min_date) else None,
                max_value=max_date.date() if pd.notna(max_date) else None,
                format="DD/MM/YYYY"
            )

        if start_date and end_date:

            if start_date <= end_date:

                df_master = df_master[
                    (df_master[date_column] >= pd.Timestamp(start_date))
                    &
                    (df_master[date_column] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
                ].copy()

                st.caption(
                    f"Periode: {start_date.strftime('%d %B %Y')} "
                    f"s.d. {end_date.strftime('%d %B %Y')}"
                )

            else:
                st.error("Tanggal mulai tidak boleh melebihi tanggal akhir.")
                st.stop()

    else:
        st.warning("Kolom Event Date Start tidak ditemukan.")

    # Pecah nama TS berdasarkan koma
    df_ts = df_master.copy()

    df_ts["Training Support"] = (
        df_ts["Training Support"]
        .fillna("")
        .astype(str)
        .str.split(",")
    )

    df_ts = df_ts.explode("Training Support")

    df_ts["Training Support"] = (
        df_ts["Training Support"].str.strip()
    )

    df_ts = df_ts[
        df_ts["Training Support"] != ""
    ].copy()

    # Hindari TS yang sama tercatat dua kali
    # dalam satu event
    df_ts = df_ts.drop_duplicates(
        subset=["Event ID", "Training Support"]
    )

# =========================================================
# REKAP RATA-RATA HASIL PER TRAINING SUPPORT
# =========================================================

st.subheader("Rekap Hasil per Training Support")

# Kolom sumber dan nama indikator pada dashboard
metric_columns = {
    "Rata-rata NPS": "lim 1 Net Promote Score",
    "Rata-rata UBPP Penyelenggaraan": "Lim 1 UBPP Penyelenggaraan",
    "Rata-rata % Completion Rate LIM 1": "Completion Rate Lim 1",
    "Rata-rata % Completion Rate Pretest": "Lim 2 Completion Rate Pre Test",
    "Rata-rata % Completion Rate Postest": "Lim 2 Completion Rate Post Test",
    "Rata-rata % Completion Rate Learner After": "Lim 3 Completion Learner After",
    "Rata-rata % Completion Rate SPV After": "Lim 3 Completion Supervisor After",
}

required_columns = ["Event ID", "Training Support"] + list(metric_columns.values())

missing_columns = [
    col for col in required_columns
    if col not in df_master.columns
]

if missing_columns:
    st.error(
        "Kolom berikut tidak ditemukan dalam Master Data: "
        + ", ".join(missing_columns)
    )
else:
    # Ambil data dari Master Data yang sudah difilter periode
    df_rekap_ts = df_master[required_columns].copy()

    # Pisahkan beberapa nama TS dalam satu sel
    df_rekap_ts["Training Support"] = (
        df_rekap_ts["Training Support"]
        .fillna("")
        .astype(str)
        .str.split(r"[,;\n]+", regex=True)
    )

    df_rekap_ts = df_rekap_ts.explode("Training Support")

    df_rekap_ts["Training Support"] = (
        df_rekap_ts["Training Support"].astype(str).str.strip()
    )

    # Hapus nama TS kosong
    df_rekap_ts = df_rekap_ts[
        df_rekap_ts["Training Support"].ne("")
    ].copy()

    # Samakan nama TS yang berbeda kapitalisasi
    # Contoh: Yetty Anggraini dan Yetty anggraini
    df_rekap_ts["_TS_KEY"] = (
        df_rekap_ts["Training Support"].str.casefold()
    )

    # Satu event hanya dihitung satu kali untuk setiap TS
    df_rekap_ts = df_rekap_ts.drop_duplicates(
        subset=["Event ID", "_TS_KEY"]
    )

    # Konversi indikator menjadi angka
    for col in metric_columns.values():
        df_rekap_ts[col] = pd.to_numeric(
            df_rekap_ts[col], errors="coerce"
        )

    # Nama TS untuk tampilan
    nama_ts = (
        df_rekap_ts.groupby("_TS_KEY")["Training Support"]
        .first()
        .to_dict()
    )

    # Hitung rata-rata masing-masing indikator
    rekap_ts = (
        df_rekap_ts
        .groupby("_TS_KEY")
        .agg(
            **{
                nama: (kolom, "mean")
                for nama, kolom in metric_columns.items()
            },
            **{
                "Jumlah Event": ("Event ID", "nunique")
            }
        )
        .reset_index()
    )

    rekap_ts["Training Support"] = (
        rekap_ts["_TS_KEY"].map(nama_ts)
    )

    # Susunan kolom dashboard
    output_columns = [
        "Training Support",
        "Jumlah Event",
        *metric_columns.keys()
    ]

    rekap_ts = rekap_ts[output_columns]

    # Urutkan berdasarkan nama TS
    rekap_ts = rekap_ts.sort_values(
        "Training Support"
    ).reset_index(drop=True)

    # Tampilkan tabel
    st.dataframe(
        rekap_ts,
        use_container_width=True,
        hide_index=True,
        column_config={
            col: st.column_config.NumberColumn(
                col,
                format="%.2f"
            )
            for col in metric_columns.keys()
        }
    )

    # Download hasil rekap ke Excel
    import io

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        rekap_ts.to_excel(
            writer,
            index=False,
            sheet_name="Rekap Per TS"
        )

    st.download_button(
        label="📥 Download Rekap Per TS",
        data=output.getvalue(),
        file_name="Rekap_Hasil_Per_Training_Support.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# =========================================================
# 3 TAB RANKING PERFORMANCE TRAINING SUPPORT
# =========================================================

st.divider()
st.subheader("🏆 Ranking Performance Training Support")

tab_nps, tab_ubpp, tab_lim1 = st.tabs([
    "🏆 Ranking NPS",
    "🏆 Ranking UBPP",
    "🏆 Ranking Completion Rate LIM 1"
])

ranking_metrics = {
    "NPS": "Rata-rata NPS",
    "UBPP": "Rata-rata UBPP Penyelenggaraan",
    "LIM1": "Rata-rata % Completion Rate LIM 1"
}


def tampilkan_ranking(metric_col, judul):
    ranking_df = rekap_ts[
        ["Training Support", "Jumlah Event", metric_col]
    ].copy()

    ranking_df = ranking_df.dropna(subset=[metric_col])

    ranking_df = ranking_df.sort_values(
        by=metric_col,
        ascending=False
    ).reset_index(drop=True)

    if ranking_df.empty:
        st.info("Belum ada data untuk indikator ini.")
        return

    ranking_df.insert(
        0,
        "Peringkat",
        ranking_df[metric_col].rank(
            method="min",
            ascending=False
        ).astype(int)
    )

    st.markdown(f"### {judul}")

    st.dataframe(
        ranking_df,
        use_container_width=True,
        hide_index=True
    )


with tab_nps:
    tampilkan_ranking(
        ranking_metrics["NPS"],
        "Peringkat NPS Tertinggi"
    )

with tab_ubpp:
    tampilkan_ranking(
        ranking_metrics["UBPP"],
        "Peringkat UBPP Penyelenggaraan Tertinggi"
    )

with tab_lim1:
    tampilkan_ranking(
        ranking_metrics["LIM1"],
        "Peringkat Completion Rate LIM 1 Tertinggi"
    )
