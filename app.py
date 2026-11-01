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

    
    # ==========================================
    # PIVOT DASHBOARD
    # ==========================================

    st.divider()
    st.header("PIVOT ANALYTICS")

    def numeric_column(data, column):
        if column not in data.columns:
            return pd.Series(index=data.index, dtype="float64")

        return pd.to_numeric(
            data[column].astype(str).str.replace("%", "", regex=False),
            errors="coerce"
        )

    def percentage_column(data, column):
        values = numeric_column(data, column)

        # Data sumber menggunakan skala 0-100.
        # Ubah menjadi 0-1 agar format persentase konsisten.
        if values.dropna().gt(1).any():
            values = values / 100

        return values

    # ------------------------------------------
    # 1. BREAKDOWN SCORE UBPP
    # ------------------------------------------

    st.subheader("1. Breakdown Score UBPP Penyelenggaraan")

    ubpp_col = "Lim 1 UBPP Penyelenggaraan"

    if ubpp_col in df.columns:

        ubpp = numeric_column(df, ubpp_col)

        score_category = pd.cut(
            ubpp,
            bins=[-float("inf"), 65, 85, 90, float("inf")],
            labels=["<65", "65-84", "85-90", ">90"],
            right=False
        )

        score_pivot = (
            score_category.value_counts(sort=False)
            .rename_axis("Kategori UBPP")
            .reset_index(name="Jumlah Event")
        )

        st.dataframe(
            score_pivot,
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------
    # 2. DISTRIBUSI EVENT
    # ------------------------------------------

    st.subheader("2. Distribusi Event")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Distribusi berdasarkan Provider**")

        if "Provider" in df.columns:
            provider_pivot = (
                df["Provider"]
                .fillna("Tidak tersedia")
                .value_counts()
                .rename_axis("Provider")
                .reset_index(name="Jumlah Event")
            )

            st.dataframe(
                provider_pivot,
                use_container_width=True,
                hide_index=True
            )

    with col2:
        st.markdown("**Distribusi berdasarkan Event Status**")

        if "Event Status" in df.columns:
            status_pivot = (
                df["Event Status"]
                .fillna("Tidak tersedia")
                .value_counts()
                .rename_axis("Event Status")
                .reset_index(name="Jumlah Event")
            )

            st.dataframe(
                status_pivot,
                use_container_width=True,
                hide_index=True
            )

    # ------------------------------------------
    # 3. DELIVERY METHOD
    # ------------------------------------------

    st.subheader("3. Distribusi Delivery Method")

    if "Delivery Method" in df.columns:

        delivery_pivot = (
            df["Delivery Method"]
            .fillna("Tidak tersedia")
            .value_counts()
            .rename_axis("Delivery Method")
            .reset_index(name="Jumlah Event")
        )

        st.dataframe(
            delivery_pivot,
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------
    # 4. TRAINING SUPPORT UPDATE
    # ------------------------------------------

    st.subheader("4. Training Support Update")

    ts_metrics = {
        "lim 1 Net Promote Score": "Rata-rata NPS",
        "Lim 1 UBPP Penyelenggaraan": "Rata-rata UBPP Penyelenggaraan",
        "Completion Rate Lim 1": "Completion Rate LIM 1",
        "Lim 2 Completion Rate Pre Test": "Completion Rate Pretest",
        "Lim 2 Completion Rate Post Test": "Completion Rate Posttest",
        "Lim 3 Completion Learner After": "Completion Rate Learner After",
        "Lim 3 Completion Supervisor After": "Completion Rate SPV After"
    }

    available_metrics = {
        source: label
        for source, label in ts_metrics.items()
        if source in df.columns
    }

    if "Training Support" in df.columns and available_metrics:

        ts_data = df[["Training Support"]].copy()

        for source, label in available_metrics.items():

            if "Completion Rate" in source:
                ts_data[label] = percentage_column(df, source)
            else:
                ts_data[label] = numeric_column(df, source)

        ts_pivot = (
            ts_data
            .groupby("Training Support", dropna=False)
            .mean(numeric_only=True)
            .reset_index()
        )

        st.dataframe(
            ts_pivot.style.format({
                col: "{:.2%}" if "Completion Rate" in col else "{:.2f}"
                for col in ts_pivot.columns
                if col != "Training Support"
            }),
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------
    # 5. EVENT STATUS PER TRAINING SUPPORT
    # ------------------------------------------

    st.subheader("5. Event Status per Training Support")

    if {"Training Support", "Event Status"}.issubset(df.columns):

        ts_status = pd.pivot_table(
            df,
            index="Training Support",
            columns="Event Status",
            values="Event ID",
            aggfunc="nunique",
            fill_value=0,
            margins=True,
            margins_name="Total Keseluruhan"
        ).reset_index()

        st.dataframe(
            ts_status,
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------
    # 6. DELIVERY METHOD PER TRAINING SUPPORT
    # ------------------------------------------

    st.subheader("6. Delivery Method per Training Support")

    if {"Training Support", "Delivery Method"}.issubset(df.columns):

        ts_delivery = pd.pivot_table(
            df,
            index="Training Support",
            columns="Delivery Method",
            values="Event ID",
            aggfunc="nunique",
            fill_value=0,
            margins=True,
            margins_name="Total Keseluruhan"
        ).reset_index()

        st.dataframe(
            ts_delivery,
            use_container_width=True,
            hide_index=True
        )

    # ------------------------------------------
    # 7. LEADERBOARD TRAINING SUPPORT
    # ------------------------------------------

    st.subheader("7. Leaderboard Training Support")

    if "Training Support" in df.columns:

        leaderboard_data = df[["Training Support"]].copy()

        leaderboard_metrics = {
            "lim 1 Net Promote Score": "NPS",
            "Lim 1 UBPP Penyelenggaraan": "UBPP Penyelenggaraan",
            "Completion Rate Lim 1": "Completion Rate LIM 1"
        }

        for source, label in leaderboard_metrics.items():
            if source in df.columns:
                if "Completion Rate" in source:
                    leaderboard_data[label] = percentage_column(df, source)
                else:
                    leaderboard_data[label] = numeric_column(df, source)

        leaderboard = (
            leaderboard_data
            .groupby("Training Support")
            .mean(numeric_only=True)
            .reset_index()
        )

        metric_tabs = st.tabs(
            [c for c in leaderboard.columns if c != "Training Support"]
        )

        for tab, metric in zip(
            metric_tabs,
            [c for c in leaderboard.columns if c != "Training Support"]
        ):
            with tab:

                ranking = leaderboard[
                    ["Training Support", metric]
                ].dropna().sort_values(
                    metric,
                    ascending=False
                )

                ranking.insert(
                    0,
                    "Rank",
                    range(1, len(ranking) + 1)
                )

                st.dataframe(
                    ranking.style.format({
                        metric: "{:.2%}" if metric == "Completion Rate LIM 1" else "{:.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

    # ------------------------------------------
    # 8. WORKLOAD PER TRAINING SUPPORT
    # ------------------------------------------

    st.subheader("8. Workload per Training Support")

    if {"Training Support", "Event ID"}.issubset(df.columns):

        workload = (
            df.groupby("Training Support")["Event ID"]
            .nunique()
            .reset_index(name="Jumlah Event")
            .sort_values("Jumlah Event", ascending=False)
        )

        st.dataframe(
            workload,
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "Silakan upload file Master Data Excel melalui menu Data Control."
    )
