import streamlit as st

from modules.data_source import (
    load_master_data,
    get_sync_time
)

st.set_page_config(
    page_title="TCU Area Performance",
    page_icon="📊",
    layout="wide"
)

st.title("TCU Area Performance")
st.caption("Training Performance Analytics Dashboard")

st.sidebar.header("Data Control")

if st.sidebar.button("Refresh Master Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Mengambil Master Data..."):
        df = load_master_data()

    st.success("Master Data berhasil dimuat.")

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
        f"Terakhir dimuat: {get_sync_time()}"
    )

    st.subheader("Preview Master Data")

    st.dataframe(
        df.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Struktur Kolom")

    st.dataframe(
        df.dtypes.astype(str)
        .rename("Tipe Data")
        .reset_index()
        .rename(columns={"index": "Nama Kolom"}),
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error("Gagal mengambil Master Data.")
    st.exception(e)

