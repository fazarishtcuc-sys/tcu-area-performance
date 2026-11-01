import io
import re
import pandas as pd
import streamlit as st

from modules.data_source import load_master_data, get_sync_time

st.set_page_config(
    page_title="TCU Area Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- Styling -------------------------
st.markdown("""
<style>
    .stApp { background: #f5f7fb; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1600px; }
    [data-testid="stSidebar"] { background: #101b35; }
    [data-testid="stSidebar"] * { color: #eef3ff !important; }
    .hero {
        padding: 1.25rem 1.5rem; border-radius: 18px;
        background: linear-gradient(120deg,#14213d 0%,#244a78 60%,#287c91 100%);
        color: white; margin-bottom: 1rem;
    }
    .hero h1 { margin: 0; font-size: 1.9rem; color: white; }
    .hero p { margin: .35rem 0 0 0; color: #dbeafe; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e6eaf2; padding: 1rem;
        border-radius: 14px; box-shadow: 0 2px 8px rgba(20,33,61,.04);
    }
    div[data-testid="stTabs"] button { font-weight: 600; }
    div[data-testid="stDataFrame"] { border: 1px solid #e6eaf2; border-radius: 12px; }
    .section-note { color: #64748b; font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📊 TCU Area Performance</h1>
  <p>Training Performance Analytics · Dashboard evaluasi dan rekapitulasi</p>
</div>
""", unsafe_allow_html=True)

# ------------------------- Session state / upload -------------------------
if "master_df" not in st.session_state:
    st.session_state.master_df = None
if "sync_time" not in st.session_state:
    st.session_state.sync_time = None

with st.sidebar:
    st.markdown("## Data Control")
    uploaded_file = st.file_uploader(
        "Upload Master Data (.xlsx)", type=["xlsx"], key="master_upload"
    )
    if st.button("↻ Reset / Muat Ulang", use_container_width=True):
        st.session_state.master_df = None
        st.session_state.sync_time = None
        st.rerun()
    st.caption("Unggah file Master Data untuk memperbarui dashboard.")

if uploaded_file is not None:
    try:
        with st.spinner("Membaca Master Data..."):
            loaded = load_master_data(uploaded_file)
            if not isinstance(loaded, pd.DataFrame):
                raise ValueError("Loader tidak menghasilkan DataFrame.")
            st.session_state.master_df = loaded.copy()
            st.session_state.sync_time = get_sync_time()
        st.sidebar.success("Master Data berhasil dimuat.")
    except Exception as exc:
        st.error(f"Gagal membaca Master Data: {exc}")

df = st.session_state.master_df
if df is None:
    st.info("Silakan upload file Master Data (.xlsx) melalui panel sebelah kiri.")
    st.stop()

df_master = df.copy()

# ------------------------- Helpers -------------------------
def parse_numeric(series):
    """Convert numeric values including percent/comma decimal formats."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.fillna("").astype(str).str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")

def split_names(series):
    return series.fillna("").astype(str).str.split(r"[,;\n]+")

def add_total_row(data, metric_columns, label_col):
    total = {label_col: "RATA-RATA"}
    for name in metric_columns:
        total[name] = data[name].mean() if name in data else float("nan")
    return pd.concat([data, pd.DataFrame([total])], ignore_index=True)

def area_summary(source, metric_map, areas):
    needed = ["Event ID", "Provider", *metric_map.values()]
    missing = [c for c in needed if c not in source.columns]
    if missing:
        return None, missing
    area_data = source[needed].copy()
    area_data["Provider"] = split_names(area_data["Provider"])
    area_data = area_data.explode("Provider")
    area_data["Provider"] = area_data["Provider"].astype(str).str.strip()
    area_data = area_data[area_data["Provider"].isin(areas)].copy()
    for col in metric_map.values():
        area_data[col] = parse_numeric(area_data[col])
    area_data = area_data.drop_duplicates(["Event ID", "Provider"])
    agg = {label: (col, "mean") for label, col in metric_map.items()}
    result = area_data.groupby("Provider").agg(**agg).reindex(areas).reset_index()
    result = result.rename(columns={"Provider": "TCU Area"})
    return add_total_row(result, list(metric_map.keys()), "TCU Area"), []

def make_ts_summary(source, metric_map):
    needed = ["Event ID", "Training Support", *metric_map.values()]
    missing = [c for c in needed if c not in source.columns]
    if missing:
        return None, missing
    data = source[needed].copy()
    data["Training Support"] = split_names(data["Training Support"])
    data = data.explode("Training Support")
    data["Training Support"] = data["Training Support"].astype(str).str.strip()
    data = data[data["Training Support"].ne("")].copy()
    data["_TS_KEY"] = data["Training Support"].str.casefold()
    data = data.drop_duplicates(["Event ID", "_TS_KEY"])
    for col in metric_map.values():
        data[col] = parse_numeric(data[col])
    names = data.groupby("_TS_KEY")["Training Support"].first().to_dict()
    agg = {label: (col, "mean") for label, col in metric_map.items()}
    agg["Jumlah Event"] = ("Event ID", "nunique")
    result = data.groupby("_TS_KEY").agg(**agg).reset_index()
    result["Training Support"] = result["_TS_KEY"].map(names)
    result = result[["Training Support", "Jumlah Event", *metric_map.keys()]]
    return result.sort_values("Training Support").reset_index(drop=True), []

def numeric_config(columns, fmt="%.2f"):
    return {c: st.column_config.NumberColumn(c, format=fmt) for c in columns}

# ------------------------- Date filter -------------------------
st.markdown("### 🗓️ Filter Periode")
date_col = "Event Date Start"
if date_col not in df_master.columns:
    st.error(f"Kolom wajib **{date_col}** tidak ditemukan dalam Master Data.")
    st.stop()

df_master[date_col] = pd.to_datetime(df_master[date_col], errors="coerce", dayfirst=True)
valid_dates = df_master[date_col].dropna()
if valid_dates.empty:
    st.error(f"Kolom **{date_col}** tidak memiliki tanggal yang valid.")
    st.stop()

min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    start_date = st.date_input("Tanggal Mulai", value=min_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
with c2:
    end_date = st.date_input("Tanggal Akhir", value=max_date, min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
with c3:
    st.markdown("<div class='section-note'>Filter berdasarkan <b>Event Date Start</b>. Event dihitung jika tanggal mulai berada di dalam periode.</div>", unsafe_allow_html=True)

if start_date > end_date:
    st.error("Tanggal mulai tidak boleh melebihi tanggal akhir.")
    st.stop()

df_master = df_master[
    df_master[date_col].ge(pd.Timestamp(start_date))
    & df_master[date_col].lt(pd.Timestamp(end_date) + pd.Timedelta(days=1))
].copy()

st.caption(f"Periode aktif: {start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}")

# KPI summary
event_count = df_master["Event ID"].nunique() if "Event ID" in df_master.columns else len(df_master)
ts_count = 0
if "Training Support" in df_master.columns:
    ts_tmp = df_master[["Event ID", "Training Support"]].copy() if "Event ID" in df_master.columns else df_master[["Training Support"]].copy()
    ts_tmp["Training Support"] = split_names(ts_tmp["Training Support"])
    ts_tmp = ts_tmp.explode("Training Support")
    ts_tmp["Training Support"] = ts_tmp["Training Support"].astype(str).str.strip()
    ts_tmp = ts_tmp[ts_tmp["Training Support"].ne("")]
    if "Event ID" in ts_tmp.columns:
        ts_tmp = ts_tmp.drop_duplicates(["Event ID", "Training Support"])
    ts_count = ts_tmp["Training Support"].nunique()

k1, k2, k3 = st.columns(3)
k1.metric("Event dalam Periode", f"{event_count:,}")
k2.metric("Training Support Terlibat", f"{ts_count:,}")
k3.metric("Baris Master Data", f"{len(df_master):,}")
if st.session_state.sync_time:
    st.caption(f"Data terakhir dimuat: {st.session_state.sync_time}")

# ------------------------- Metric mappings -------------------------
area_list = ["TCU Area 1 Jakarta", "TCU Area 2 Bandung", "TCU Area 4 Makassar"]

completion_metrics = {
    "Rata-rata % Completion Rate LIM 1": "Completion Rate Lim 1",
    "Rata-rata % Completion Rate (Pretest)": "Lim 2 Completion Rate Pre Test",
    "Rata-rata % Completion Rate (Postest)": "Lim 2 Completion Rate Post Test",
    "Rata-rata % Completion Rate Learner After": "Lim 3 Completion Learner After",
    "Rata-rata % Completion Rate SPV After": "Lim 3 Completion Supervisor After",
}
score_metrics = {
    "Rata-rata NET PROMOTE SCORE (NPS)": "lim 1 Net Promote Score",
    "Rata-rata FINAL SCORE LIM 1": "Lim 1 Final Score",
    "Rata-rata UBPP PENYELENGGARAAN": "Lim 1 UBPP Penyelenggaraan",
    "Rata-rata UBPP SARANA": "Lim 1 UBPP Sarana",
    "Rata-rata CUSTOMER SATISFACTION": "Lim 1 Customer Satisfaction",
}
ts_metrics = {
    "Rata-rata NPS": "lim 1 Net Promote Score",
    "Rata-rata UBPP Penyelenggaraan": "Lim 1 UBPP Penyelenggaraan",
    "Rata-rata % Completion Rate LIM 1": "Completion Rate Lim 1",
    "Rata-rata % Completion Rate Pretest": "Lim 2 Completion Rate Pre Test",
    "Rata-rata % Completion Rate Postest": "Lim 2 Completion Rate Post Test",
    "Rata-rata % Completion Rate Learner After": "Lim 3 Completion Learner After",
    "Rata-rata % Completion Rate SPV After": "Lim 3 Completion Supervisor After",
}

# ------------------------- Area performance -------------------------
st.markdown("## 🏢 Performance per TCU Area")
tab_completion, tab_score = st.tabs(["Completion Rate LIM 1", "Score LIM 1"])

with tab_completion:
    result, missing = area_summary(df_master, completion_metrics, area_list)
    if missing:
        st.error("Kolom tidak ditemukan: " + ", ".join(missing))
    else:
        st.dataframe(result, use_container_width=True, hide_index=True, column_config=numeric_config(completion_metrics.keys()), height=260)

with tab_score:
    result, missing = area_summary(df_master, score_metrics, area_list)
    if missing:
        st.error("Kolom tidak ditemukan: " + ", ".join(missing))
    else:
        st.dataframe(result, use_container_width=True, hide_index=True, column_config=numeric_config(score_metrics.keys()), height=260)

# ------------------------- Training Support summary -------------------------
st.markdown("## 👥 Rekap Hasil per Training Support")
rekap_ts, missing_ts = make_ts_summary(df_master, ts_metrics)
if missing_ts:
    st.error("Kolom tidak ditemukan: " + ", ".join(missing_ts))
    st.stop()

st.dataframe(
    rekap_ts, use_container_width=True, hide_index=True,
    column_config={"Jumlah Event": st.column_config.NumberColumn("Jumlah Event", format="%d"), **numeric_config(ts_metrics.keys())},
    height=420,
)

# Excel export: summary plus rankings and area summaries
def ranking_frame(data, metric_col):
    ranked = data[["Training Support", "Jumlah Event", metric_col]].dropna(subset=[metric_col]).copy()
    ranked = ranked.sort_values(metric_col, ascending=False).reset_index(drop=True)
    if ranked.empty:
        return ranked
    ranked.insert(0, "Peringkat", ranked[metric_col].rank(method="min", ascending=False).astype(int))
    return ranked

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    rekap_ts.to_excel(writer, index=False, sheet_name="Rekap Per TS")
    for sheet_name, metric_col in [
        ("Ranking NPS", "Rata-rata NPS"),
        ("Ranking UBPP", "Rata-rata UBPP Penyelenggaraan"),
        ("Ranking LIM 1", "Rata-rata % Completion Rate LIM 1"),
    ]:
        ranking_frame(rekap_ts, metric_col).to_excel(writer, index=False, sheet_name=sheet_name)
    area_completion, missing_completion = area_summary(df_master, completion_metrics, area_list)
    if not missing_completion:
        area_completion.to_excel(writer, index=False, sheet_name="Performance Area LIM1")
    area_score, missing_score = area_summary(df_master, score_metrics, area_list)
    if not missing_score:
        area_score.to_excel(writer, index=False, sheet_name="Performance Area Score")

st.download_button(
    "⬇️ Download Rekap Dashboard (Excel)",
    data=excel_buffer.getvalue(),
    file_name="TCU_Area_Performance.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
