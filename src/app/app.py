import sys
import os

# Add the root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(root_dir)

import streamlit as st
from src.app.tabs.tab_upload import render as render_upload
from src.app.tabs.tab_cleaned_data import render as render_cleaned_data
from src.app.tabs.tab_daily import render as render_daily
from src.app.tabs.tab_weekly import render as render_weekly
from src.app.tabs.tab_monthly import render as render_monthly
from src.app.tabs.tab_ytd import render as render_ytd
from src.config.settings import APP_TITLE, VERSION

# Configure Streamlit
st.set_page_config(page_title=APP_TITLE, layout="wide")

# App Title
st.title(APP_TITLE)
st.write(f"Version: {VERSION}")

# Tabs
tabs = st.tabs(["Data Upload", "Cleaned Data", "Daily Dashboard", "Weekly Dashboard", "Monthly Dashboard", "YTD Dashboard"])

# Render Tabs
with tabs[0]:
    render_upload()

with tabs[1]:
    render_cleaned_data()

with tabs[2]:
    render_daily()

with tabs[3]:
    render_weekly()

with tabs[4]:
    render_monthly()

with tabs[5]:
    render_ytd()