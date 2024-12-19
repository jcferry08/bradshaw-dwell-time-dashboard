import pandas as pd
import numpy as np
import duckdb

# Cleaning Open Dock for No Show Data Set
def clean_open_dock_no_shows(od_df):
    import streamlit as st
    # Standardize column names by stripping whitespace and lowercasing
    od_df.columns = od_df.columns.str.strip().str.lower()

    # Rename columns for consistency
    od_df.rename(columns={"appt date": "appointment datetime"}, inplace=True)

    # Filter for non-Inbound rows
    if "direction" in od_df.columns:
        od_df = od_df[od_df["direction"].str.lower() != "inbound"]
    else:
        raise KeyError("'Direction' column is missing in the Open Dock CSV.")

    # Keep only rows where 'Status' is 'Completed' or 'NoShow'
    if "status" in od_df.columns:
        od_df = od_df[od_df["status"].isin(["Completed", "NoShow"])]
    else:
        raise KeyError("'Status' column is missing in the Open Dock CSV.")

    # Select relevant columns
    if "appointment datetime" in od_df.columns and "status" in od_df.columns:
        no_show_data = od_df[["appointment datetime", "status"]].dropna()
    else:
        raise KeyError("Required columns 'appointment datetime' or 'status' are missing after cleaning.")

    # Set data types
    no_show_data['appointment datetime'] = pd.to_datetime(no_show_data['appointment datetime'], errors='coerce')
    no_show_data['status'] = no_show_data['status'].astype(str)

    no_show_data = no_show_data[no_show_data['status'] != 'Completed']

    no_show_data['Week'] = no_show_data['appointment datetime'].dt.isocalendar().week
    no_show_data['Month'] = no_show_data['appointment datetime'].dt.month

    # Save no_show_data in session state
    if 'no_show_data' not in st.session_state:
        st.session_state['no_show_data'] = no_show_data

    return no_show_data

# Cleaning Open Order CSV
def clean_open_order(oo_df):
    oo_df.columns = oo_df.columns.str.strip()

    # Keep necessary columns
    columns_to_keep = ['Appt Date and Time', 'SO #', 'Shipment Nbr', 'Order Status']
    oo_df = oo_df[columns_to_keep]

    # Clean 'Appt Date and Time'
    oo_df['Appt Date and Time'] = pd.to_datetime(oo_df['Appt Date and Time'].str.strip(), errors='coerce')
    oo_df = oo_df.dropna(subset=['Appt Date and Time'])

    # Clean 'SO #' and 'Shipment Nbr'
    oo_df['SO #'] = oo_df['SO #'].astype(str).str.strip()
    oo_df['Shipment Nbr'] = oo_df['Shipment Nbr'].astype(str).str.replace(',', '').str.extract(r'(\d+)', expand=False).fillna('')
    
    # Filter for 'shipped' orders
    oo_df = oo_df[oo_df['Order Status'].str.strip().str.lower() == 'shipped']

    # Combine SO Numbers for the same Shipment Nbr
    oo_df = oo_df.groupby('Shipment Nbr', as_index=False).agg({
        'Appt Date and Time': 'first',
        'SO #': lambda x: ', '.join(sorted(set(x))),
    })

    oo_df.rename(columns={
        'Shipment Nbr': 'Shipment ID',
        'Appt Date and Time': 'Appt DateTime',
        'SO #': 'SO Number'
    }, inplace=True)

    return oo_df

# Cleaning Trailer Activity CSV
def clean_trailer_activity(ta_df):
    ta_df.columns = ta_df.columns.str.strip()

    # Keep necessary columns
    columns_to_keep = [
        'CHECKIN DATE TIME', 'APPOINTMENT DATE TIME', 'CHECKOUT DATE TIME',
        'CARRIER', 'VISIT TYPE', 'ACTIVITY TYPE', 'SHIPMENT_ID', 'Date/Time'
    ]
    ta_df = ta_df[columns_to_keep]

    # Filter for activity type and visit type
    ta_df = ta_df[(ta_df['ACTIVITY TYPE'] == 'CLOSED') &
                  (ta_df['VISIT TYPE'].isin(['Pickup Load', 'Live Load']))]

    # Clean 'SHIPMENT_ID'
    ta_df['SHIPMENT_ID'] = ta_df['SHIPMENT_ID'].astype(str).str.replace(',', '').str.extract(r'(\d+)', expand=False).fillna('')

    # Convert date/time columns
    datetime_columns = ['CHECKIN DATE TIME', 'APPOINTMENT DATE TIME', 'CHECKOUT DATE TIME', 'Date/Time']
    for col in datetime_columns:
        ta_df[col] = pd.to_datetime(ta_df[col].str.strip(), errors='coerce')

    # Drop rows with invalid dates
    ta_df = ta_df.dropna(subset=['APPOINTMENT DATE TIME', 'CHECKIN DATE TIME', 'CHECKOUT DATE TIME'])

    # Calculate 'Required Time'
    def required_time(row):
        if row['VISIT TYPE'] == 'Live Load':
            return row['APPOINTMENT DATE TIME'] + pd.Timedelta(minutes=15)
        return row['APPOINTMENT DATE TIME'] + pd.Timedelta(hours=24)

    ta_df['Required Time'] = ta_df.apply(required_time, axis=1)

    # Determine Compliance
    def compliance(row):
        if row['CHECKIN DATE TIME'] <= row['Required Time']:
            return 'On Time'
        return 'Late'

    ta_df['Compliance'] = ta_df.apply(compliance, axis=1)

    ta_df.rename(columns={
        'CHECKIN DATE TIME': 'Checkin DateTime',
        'CHECKOUT DATE TIME': 'Checkout DateTime',
        'CARRIER': 'Carrier',
        'VISIT TYPE': 'Visit Type',
        'SHIPMENT_ID': 'Shipment ID',
        'Date/Time': 'Loaded DateTime'
    }, inplace=True)

    return ta_df

# Merging Cleaned Data
def clean_and_merge_compliance(oo_df, ta_df):
    cleaned_open_order = clean_open_order(oo_df)
    cleaned_trailer_activity = clean_trailer_activity(ta_df)

    # Merge datasets using DuckDB
    con = duckdb.connect(":memory:")
    con.register("open_order", cleaned_open_order)
    con.register("trailer_activity", cleaned_trailer_activity)

    query = """
    SELECT 
        open_order."Shipment ID",
        open_order."SO Number",
        open_order."Appt DateTime",
        trailer_activity."Checkin DateTime",
        trailer_activity."Checkout DateTime",
        trailer_activity."Required Time",
        trailer_activity."Loaded DateTime",
        trailer_activity."Carrier",
        trailer_activity."Visit Type",
        trailer_activity."Compliance"
    FROM open_order
    LEFT JOIN trailer_activity
    ON open_order."Shipment ID" = trailer_activity."Shipment ID"
    """

    merged_df = con.execute(query).fetchdf()

    # Set data types and calculate derived metrics
    merged_df['Shipment ID'] = merged_df['Shipment ID'].astype(str).fillna("Unknown")
    merged_df['SO Number'] = merged_df['SO Number'].astype(str)

    datetime_columns = ['Appt DateTime', 'Checkin DateTime', 'Checkout DateTime', 'Required Time', 'Loaded DateTime']
    for col in datetime_columns:
        merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce')

    merged_df['Carrier'] = merged_df['Carrier'].fillna("Unknown").astype(str)
    merged_df['Visit Type'] = merged_df['Visit Type'].fillna("Unknown").astype(str)
    merged_df['Compliance'] = merged_df['Compliance'].fillna("Unknown").astype(str)

    # Calculate dwell time
    merged_df["Dwell Time"] = merged_df.apply(calculate_dwell_time, axis=1)

    # Add Scheduled Date, Week, and Month columns
    merged_df['Scheduled Date'] = merged_df['Appt DateTime'].dt.date
    merged_df['Week'] = merged_df['Appt DateTime'].dt.isocalendar().week
    merged_df['Month'] = merged_df['Appt DateTime'].dt.month

    # Remove rows where Compliance is "Unknown"
    merged_df = merged_df[merged_df['Compliance'] != "Unknown"]

    # Remove duplicate Shipment ID rows, keeping the one with the latest Appt DateTime
    merged_df = merged_df.sort_values(by='Appt DateTime', ascending=False).drop_duplicates(subset='Shipment ID')

    # Filter out specified carriers
    carriers_to_exclude = [
        'AACT', 'DIMS', 'EXLA', 'SAIA', 'FXFE', 'FXLA', 'FXNL', 'F106', 'F107',
        'F109', 'F110', 'F111', 'F112', 'F117', 'ODFL', 'U743', 'U746', 'U748', 'VQXX', 'CTII'
    ]
    merged_df = merged_df[~merged_df['Carrier'].isin(carriers_to_exclude)]

    return merged_df

def calculate_dwell_time(row):
    """
    Calculate dwell time based on loaded, check-in, and appointment times.
    """
    loaded_datetime = row['Loaded DateTime']
    checkin_datetime = row['Checkin DateTime']
    appt_datetime = row['Appt DateTime']
    compliance = row['Compliance']

    # Logic for dwell time
    if pd.notna(loaded_datetime):
        if compliance == 'On Time':
            dwell_time = round((loaded_datetime - appt_datetime).total_seconds() / 3600, 2)
        elif compliance == 'Late':
            dwell_time = round((loaded_datetime - checkin_datetime).total_seconds() / 3600, 2)
        else:
            dwell_time = None
    else:
        dwell_time = None

    # Ensure dwell time is valid and positive
    if dwell_time is not None and dwell_time <= 0:
        dwell_time = 0

    return dwell_time