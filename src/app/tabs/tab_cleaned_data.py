import streamlit as st
from src.utils.cleaning_utils import clean_and_merge_compliance, clean_open_dock_no_shows

def render():
    st.header("Cleaned Data")
    st.write("View and download the cleaned dataset.")

    uploaded_files = st.session_state.get("uploaded_files", {})
    if not all(file is not None for file in uploaded_files.values()):
        st.warning("Please upload all three files in the Data Upload tab.")
        return

    open_dock = uploaded_files["open_dock"]
    open_order = uploaded_files["open_order"]
    trailer_activity = uploaded_files["trailer_activity"]

    # Cleaned datasets
    st.subheader("Cleaned Datasets")

    try:
        # Process No Show Data
        no_show_data = clean_open_dock_no_shows(open_dock)
        st.session_state['no_show_data'] = no_show_data  # Save No Show Data to session state
        st.markdown("### No Show Data")
        st.dataframe(no_show_data)

        # Merged Dataset
        merged_df = clean_and_merge_compliance(open_order, trailer_activity)
        st.session_state['dwell_and_ontime_compliance'] = merged_df  # Save to session state
        st.markdown("### Dwell and On-Time Compliance Data")
        st.dataframe(merged_df)

        # Optional: Download button for No Show Data
        st.download_button(
            label="Download No Show Data as CSV",
            data=no_show_data.to_csv(index=False).encode('utf-8'),
            file_name="no_show_data.csv",
            mime="text/csv",
        )

        # Optional: Download button for Merged Data
        st.download_button(
            label="Download Merged Data as CSV",
            data=merged_df.to_csv(index=False).encode('utf-8'),
            file_name="dwell_and_ontime_compliance.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"An error occurred during data processing: {e}")
