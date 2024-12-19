import pandas as pd
import streamlit as st

def render():
    st.header("Data Upload")
    st.write("Upload your Open Dock, Open Order, and Trailer Activity files below.")

    # Initialize session state
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = {"open_dock": None, "open_order": None, "trailer_activity": None}

    # Open Dock
    open_dock = st.file_uploader("Upload Open Dock CSV", type=["csv"], key="open_dock")
    if open_dock is not None:
        st.session_state.uploaded_files["open_dock"] = pd.read_csv(open_dock, low_memory=False)
        st.subheader("Open Dock Preview")
        st.dataframe(st.session_state.uploaded_files["open_dock"].head())

    # Open Order
    open_order = st.file_uploader("Upload Open Order CSV", type=["csv"], key="open_order")
    if open_order is not None:
        st.session_state.uploaded_files["open_order"] = pd.read_csv(open_order, low_memory=False)
        st.subheader("Open Order Preview")
        st.dataframe(st.session_state.uploaded_files["open_order"].head())

    # Trailer Activity
    trailer_activity = st.file_uploader("Upload Trailer Activity CSV", type=["csv"], key="trailer_activity")
    if trailer_activity is not None:
        st.session_state.uploaded_files["trailer_activity"] = pd.read_csv(trailer_activity, low_memory=False)
        st.subheader("Trailer Activity Preview")
        st.dataframe(st.session_state.uploaded_files["trailer_activity"].head())

