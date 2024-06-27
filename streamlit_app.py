import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Set page config for wide mode
st.set_page_config(page_title="US Job Postings by Sector", layout="wide")


# Load data
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/job_postings_by_sector_US.csv"
    df = pd.read_csv(url)
    df['date'] = pd.to_datetime(df['date'])
    return df


df = load_data()


# Calculate Coefficient of Variation and Rolling Volatility
def calculate_volatility(data):
    cv = data.std() / data.mean()
    rolling_vol = data.rolling(window=30).std() / data.rolling(window=30).mean()
    return cv, rolling_vol


# Calculate volatility for all sectors
all_sectors_volatility = {}
for sector in df['display_name'].unique():
    sector_data = df[df['display_name'] == sector]
    cv, _ = calculate_volatility(sector_data['indeed_job_postings_index'])
    all_sectors_volatility[sector] = cv

# Create two columns: one narrow for controls, one wide for the chart
col1, col2 = st.columns([1, 4])

with col1:
    st.title("US Job Postings by Sector")
    st.header("Select Sectors")

    # Add Check/Uncheck All option
    select_all = st.checkbox("Select All")

    # Create checkboxes for sector selection
    sectors = df['display_name'].unique()
    sector_states = {}
    for sector in sectors:
        sector_states[sector] = st.checkbox(sector, value=select_all)

    selected_sectors = [sector for sector, state in sector_states.items() if state]

    # Add a date range selector
    date_range = st.date_input("Select date range",
                               [df['date'].min(), df['date'].max()],
                               min_value=df['date'].min(),
                               max_value=df['date'].max())

    # Show raw data option
    show_raw_data = st.checkbox("Show raw data")

with col2:
    # Filter data based on selection and date range
    filtered_df = df[
        (df['display_name'].isin(selected_sectors)) &
        (df['date'] >= pd.Timestamp(date_range[0])) &
        (df['date'] <= pd.Timestamp(date_range[1]))
        ]

    # Create subplots: one for job postings index, one for rolling volatility
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1,
                        subplot_titles=("Job Postings Index", "30-Day Rolling Volatility"))

    # Calculate and store volatility measures for selected sectors
    volatility_data = {}

    for sector in selected_sectors:
        sector_data = filtered_df[filtered_df['display_name'] == sector]

        # Add trace for job postings index
        fig.add_trace(go.Scatter(x=sector_data['date'], y=sector_data['indeed_job_postings_index'],
                                 mode='lines', name=sector), row=1, col=1)

        # Calculate volatility measures
        _, rolling_vol = calculate_volatility(sector_data['indeed_job_postings_index'])
        volatility_data[sector] = {'Rolling Volatility': rolling_vol}

        # Add trace for rolling volatility
        fig.add_trace(go.Scatter(x=sector_data['date'], y=rolling_vol,
                                 mode='lines', name=f"{sector} Volatility"), row=2, col=1)

    fig.update_layout(height=1000, title_text="Job Postings Index and Volatility by Sector")
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Indeed Job Postings Index", row=1, col=1)
    fig.update_yaxes(title_text="Coefficient of Variation", row=2, col=1)

    # Display plot
    st.plotly_chart(fig, use_container_width=True)

    # Create three columns for volatility summaries
    vol_col1, vol_col2, vol_col3 = st.columns(3)

    with vol_col1:
        st.subheader("Volatility Summary (All Sectors)")
        volatility_summary = pd.DataFrame({'Coefficient of Variation': all_sectors_volatility}).sort_values(
            'Coefficient of Variation', ascending=False)
        st.dataframe(volatility_summary)

    with vol_col2:
        st.subheader("Top 10 Lowest Volatility")
        lowest_volatility = volatility_summary.sort_values('Coefficient of Variation').head(10)
        st.dataframe(lowest_volatility)

    with vol_col3:
        st.subheader("Top 10 Highest Volatility")
        highest_volatility = volatility_summary.sort_values('Coefficient of Variation', ascending=False).head(10)
        st.dataframe(highest_volatility)

    # Display raw data if checkbox is selected
    if show_raw_data:
        st.subheader("Raw Data")
        st.dataframe(filtered_df, height=400)  # Set a fixed height for the dataframe