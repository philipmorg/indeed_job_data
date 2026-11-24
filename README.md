# US Job Postings by Sector

Explore Indeed Hiring Lab’s daily US sector indexes. The dashboard opens with
three sectors and a year of total postings. Switch to New postings to explore
that series. Search for more sectors, or select a row’s checkbox in
the sortable momentum table to add it to the trend chart. Date filters also
control the volatility ranking and raw data.

Run the app locally with [uv](https://docs.astral.sh/uv/).

```sh
uv run --with-requirements requirements.txt streamlit run streamlit_app.py
```

For a browser smoke check with `chrome-use`, use the local URL printed by
Streamlit. The default URL appears below.

```sh
chrome-use --session indeed-smoke open http://localhost:8501
chrome-use --session indeed-smoke wait --text 'Sector momentum' --timeout 20000
chrome-use --session indeed-smoke wait --selector '[data-testid=stVegaLiteChart] svg, [data-testid=stVegaLiteChart] canvas' --timeout 10000
chrome-use --session indeed-smoke wait --selector '[data-testid=stDataFrame]' --timeout 10000
```

For the full browser check, confirm that
the trend chart is populated on load, sort the momentum table and select a sector
outside the default selection, then verify that it appears in the chart. Choose a
custom start date and confirm the previous results remain visible until you choose
the end date. Open **Volatility** and change the date preset to check that the
ranking updates. Stop the server with Ctrl-C when finished.

`indeed_job_postings_data.html` is the browser-only Stlite export. Its embedded
Python should match `streamlit_app.py` when updating the export.

[Data and methodology](https://github.com/hiring-lab/job_postings_tracker)
