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

    st.success("Master Data berhasil dimuat.")

    # KPI
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Baris",
        f"{len(df):,}"
    )

    col2.metric(
        "Total Kolom",
        f"{len(df.columns):,}"
    )

    col3.metric(
        "Event ID Unik",
        f"{df['Event ID'].nunique():,}"
        if "Event ID" in df.columns else "-"
    )

    st.caption(
        f"Terakhir dimuat: {st.session_state.sync_time}"
    )

    # Preview data
    st.subheader("Preview Master Data")

    st.dataframe(
        df.head(20),
        use_container_width=True,
        hide_index=True
    )

    # Struktur kolom
    st.subheader("Struktur Kolom")

    column_info = pd.DataFrame({
        "Nama Kolom": df.columns,
        "Tipe Data": df.dtypes.astype(str).values,
        "Jumlah Data Terisi": df.notna().sum().values
    })

    st.dataframe(
        column_info,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Silakan upload file Master Data Excel melalui menu Data Control."
    )
