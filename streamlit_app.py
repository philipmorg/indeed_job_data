import altair as alt
import pandas as pd
import streamlit as st

SOURCE = "https://github.com/hiring-lab/job_postings_tracker"
DATA_URL = (
    "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/"
    "master/US/job_postings_by_sector_US.csv"
)
INDEX = "indeed_job_postings_index"
DEFAULT_SECTORS = ["Construction", "Software Development", "Nursing"]

st.set_page_config(page_title="US Job Postings by Sector", layout="wide")


@st.cache_data(ttl=3600)
def load_data():
    return (
        pd.read_csv(DATA_URL, parse_dates=["date"])
        .dropna(subset=["date", "display_name", INDEX])
        .sort_values("date")
    )


def trend_chart(data, field, label, colors):
    return (
        alt.Chart(data)
        .mark_line()
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y(f"{field}:Q", title=label, scale=alt.Scale(zero=False)),
            color=alt.Color("display_name:N", title="Sector", scale=colors),
            tooltip=[
                alt.Tooltip("display_name:N", title="Sector"),
                alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip(f"{field}:Q", title=label, format=".2f"),
            ],
        )
        .properties(height=330)
    )


st.title("US Job Postings by Sector")

try:
    df = load_data()
except (OSError, ValueError):
    st.error("Indeed Hiring Lab’s data could not be loaded. Reload the page to try again.")
    st.stop()

if df.empty:
    st.warning("Indeed Hiring Lab’s feed returned no observations.")
    st.stop()

series = st.radio("Postings series", ["Total postings", "New postings"], horizontal=True)
df = df[df["variable"] == series.lower()]

if df.empty:
    st.info("This postings series has no observations.")
    st.stop()

first, latest = df["date"].min(), df["date"].max()
st.caption(
    f"Latest observation {latest:%b %d, %Y} · [Indeed Hiring Lab]({SOURCE})"
)
with st.expander("How to read the index"):
    st.write(
        "100 represents the posting level on February 1, 2020 for each sector. "
        "An index of 110 means postings are 10% above that sector’s baseline. "
        "Indeed uses a seasonally adjusted, seven-day trailing average."
    )

sectors = sorted(df["display_name"].unique())
if "sectors" not in st.session_state:
    st.session_state.sectors = [sector for sector in DEFAULT_SECTORS if sector in sectors]
    if not st.session_state.sectors:
        st.session_state.sectors = sectors[:3]

selected = st.multiselect("Compare sectors", sectors, key="sectors")
preset = st.radio(
    "Date range", ["3 months", "1 year", "All time", "Custom"],
    index=1, horizontal=True,
)
start, end = first, latest
if preset == "3 months":
    start = max(first, latest - pd.DateOffset(months=3))
elif preset == "1 year":
    start = max(first, latest - pd.DateOffset(years=1))
elif preset == "Custom":
    dates = st.date_input(
        "Custom date range",
        (max(first, latest - pd.DateOffset(years=1)).date(), latest.date()),
        min_value=first.date(),
        max_value=latest.date(),
        key=f"custom_dates_{series}",
    )
    if len(dates) == 2:
        start, end = map(pd.Timestamp, dates)
    else:
        start, end = st.session_state.get(f"range_{series}", (start, end))
        st.caption("Choose an end date to apply the new range.")

st.session_state[f"range_{series}"] = start, end
st.caption(f"Showing {start:%b %d, %Y} to {end:%b %d, %Y}")

period = df[df["date"].between(start, end)]
chart_data = period[period["display_name"].isin(selected)]
colors = alt.Scale(domain=selected, scheme="tableau20")
alt.data_transformers.disable_max_rows()

trends_tab, volatility_tab, data_tab = st.tabs(
    ["Trends & momentum", "Volatility", "Raw data"]
)

with trends_tab:
    st.subheader("Job postings index")
    if chart_data.empty:
        st.info("Choose a sector with observations in this date range to show a trend.")
    else:
        chart = trend_chart(chart_data, INDEX, "Postings index", colors)
        baseline = alt.Chart(pd.DataFrame({"baseline": [100]})).mark_rule(
            color="#7b8190", strokeDash=[5, 4]
        ).encode(y="baseline:Q")
        st.altair_chart(baseline + chart, use_container_width=True)

    st.subheader("Sector momentum")
    if period.empty:
        st.info("No observations in this date range.")
    else:
        as_of = period["date"].max()
        month_ago = as_of - pd.Timedelta(days=30)
        year_ago = as_of - pd.DateOffset(years=1)
        levels = (
            df[df["date"].isin([as_of, month_ago, year_ago])]
            .pivot(index="display_name", columns="date", values=INDEX)
            .reindex(columns=[as_of, month_ago, year_ago])
            .dropna(subset=[as_of])
        )
        momentum = pd.DataFrame({
            "Sector": levels.index,
            "Index": levels[as_of],
            "30-day change": (levels[as_of] / levels[month_ago] - 1) * 100,
            "1-year change": (levels[as_of] / levels[year_ago] - 1) * 100,
        }).sort_values("30-day change", ascending=False).reset_index(drop=True)

        def add_sector():
            rows = st.session_state.momentum.selection.rows
            if rows:
                sector = momentum.iloc[rows[0]]["Sector"]
                if sector not in st.session_state.sectors:
                    st.session_state.sectors = [*st.session_state.sectors, sector]

        st.caption(
            f"As of {as_of:%b %d, %Y}. Select a row’s checkbox to add its sector to the chart. "
            "Changes compare against the same sector’s earlier index value."
        )
        st.dataframe(
            momentum,
            key="momentum",
            on_select=add_sector,
            selection_mode="single-row",
            hide_index=True,
            use_container_width=True,
            column_config={
                "Index": st.column_config.NumberColumn(format="%.1f"),
                "30-day change": st.column_config.NumberColumn(format="%+.1f%%"),
                "1-year change": st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )

with volatility_tab:
    st.subheader("30-day rolling volatility")
    st.caption(
        "Standard deviation as a percentage of average postings index over "
        "the trailing 30 observations. Values can use data before the chart’s start."
    )
    history = df[df["display_name"].isin(selected)].copy()
    groups = history.groupby("display_name")[INDEX]
    history["Volatility"] = groups.transform(
        lambda values: 100 * values.rolling(30).std() / values.rolling(30).mean()
    )
    rolling = history[history["date"].between(start, end)].dropna(subset=["Volatility"])
    if rolling.empty:
        st.info("Choose a sector with enough history to show rolling volatility.")
    else:
        st.altair_chart(
            trend_chart(rolling, "Volatility", "Volatility (%)", colors),
            use_container_width=True,
        )

    st.subheader("Volatility ranking")
    st.caption("All sectors ranked by how much their index varied over the selected dates.")
    summary = period.groupby("display_name")[INDEX].agg(["std", "mean"])
    ranking = (
        (100 * summary["std"] / summary["mean"])
        .dropna()
        .sort_values(ascending=False)
        .rename("Volatility (%)")
        .rename_axis("Sector")
        .reset_index()
    )
    if ranking.empty:
        st.info("Select a range with at least two observations to rank sectors.")
    else:
        st.dataframe(
            ranking, hide_index=True, use_container_width=True,
            column_config={"Volatility (%)": st.column_config.NumberColumn(format="%.2f%%")},
        )

with data_tab:
    st.subheader("Filtered observations")
    if chart_data.empty:
        st.info("Choose a sector with observations in this date range to see its data.")
    else:
        st.dataframe(
            chart_data.sort_values("date", ascending=False),
            hide_index=True,
            use_container_width=True,
        )
