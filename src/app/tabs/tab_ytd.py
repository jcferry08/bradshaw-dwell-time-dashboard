import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

def render():
    st.header("Year-To-Date Dashboard")

    # Validate session state
    if 'dwell_and_ontime_compliance' not in st.session_state:
        st.error("Dwell and On-Time Compliance data is missing. Please upload the datasets first.")
        return

    if 'no_show_data' not in st.session_state or st.session_state['no_show_data'] is None:
        st.error("No Show data is missing. Please upload the Open Dock dataset.")
        return

    compliance_data = st.session_state['dwell_and_ontime_compliance']
    no_show_data = st.session_state['no_show_data']

    # Add Year column to compliance and no_show_data
    compliance_data['Year'] = pd.DatetimeIndex(compliance_data['Scheduled Date']).year
    no_show_data['Year'] = pd.DatetimeIndex(no_show_data['appointment datetime']).year

    # Compute No Show counts by year
    no_show_by_year = no_show_data.groupby('Year').size().reset_index(name='No Show')

    # Pivot Table: Compliance Overview by Year
    compliance_pivot = compliance_data.pivot_table(
        values='Shipment ID',
        index='Year',
        columns='Compliance',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    # Add default columns for missing compliance categories
    required_columns = ['Late', 'On Time']
    for col in required_columns:
        if col not in compliance_pivot.columns:
            compliance_pivot[col] = 0

    # Merge No Show counts by year into compliance_pivot
    compliance_pivot = compliance_pivot.merge(no_show_by_year, on='Year', how='left')
    compliance_pivot['No Show'] = compliance_pivot['No Show'].fillna(0).astype(int)

    # Add Grand Total and On Time %
    compliance_pivot['Grand Total'] = compliance_pivot[['Late', 'On Time']].sum(axis=1) + compliance_pivot['No Show']
    compliance_pivot['On Time %'] = round((compliance_pivot['On Time'] / compliance_pivot['Grand Total']) * 100, 2)

    # Display Pivot Table
    st.subheader("YTD On Time Compliance by Year")
    st.table(compliance_pivot)

    # Pivot Table for On Time Compliance by Carrier
    carrier_pivot = compliance_data.pivot_table(
        values='Shipment ID',
        index='Carrier',
        columns='Compliance',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    # Add missing columns with default values of 0
    for col in required_columns:
        if col not in carrier_pivot.columns:
            carrier_pivot[col] = 0

    # Ensure numeric values for computation
    carrier_pivot['Grand Total'] = carrier_pivot[['Late', 'On Time']].sum(axis=1)
    carrier_pivot['On Time %'] = round((carrier_pivot['On Time'] / carrier_pivot['Grand Total']) * 100, 2)

    # Filter and sort by On Time % (descending order)
    carrier_pivot = carrier_pivot.sort_values(by='On Time %', ascending=False)

    # Display Pivot Table
    st.subheader("YTD On Time Compliance by Carrier")
    st.table(carrier_pivot)

    # Heatmap in an Expander
    with st.expander("YTD On Time Compliance Heatmap"):
        heatmap_data = carrier_pivot.set_index('Carrier')[['On Time %']]
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data['On Time %'].values.reshape(-1, 1),
            x=['On Time %'],
            y=heatmap_data.index,
            colorscale='RdYlGn',
            colorbar=dict(title="On Time %"),
            text=heatmap_data['On Time %'].values.reshape(-1, 1),
            texttemplate="%{text:.2f}%",
            showscale=True
        ))
        fig.update_layout(
            title='YTD On Time Compliance Percentage by Carrier',
            xaxis_title='',
            yaxis_title='Carrier',
            yaxis_autorange='reversed',
            height=len(heatmap_data) * 40 + 100
        )
        st.plotly_chart(fig, use_container_width=True)

    # Bin Dwell Time into Categories
    dwell_bins = [0, 2, 3, 4, 5, float('inf')]
    dwell_labels = ['less than 2 hours', '2 to 3 hours', '3 to 4 hours', '4 to 5 hours', '5 or more hours']
    compliance_data['Dwell Time Category'] = pd.cut(
        compliance_data['Dwell Time'], bins=dwell_bins, labels=dwell_labels, right=False
    )

    # Pivot Table: Dwell Time
    dwell_pivot = compliance_data.pivot_table(
        values='Shipment ID',
        index='Dwell Time Category',
        columns='Compliance',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    # Add Grand Total, Late %, and On Time %
    for col in ['Late', 'On Time']:
        if col not in dwell_pivot.columns:
            dwell_pivot[col] = 0

    dwell_pivot['Grand Total'] = dwell_pivot[['Late', 'On Time']].sum(axis=1)
    dwell_pivot['Late % of Total'] = round((dwell_pivot['Late'] / dwell_pivot['Grand Total']) * 100, 2)
    dwell_pivot['On Time % of Total'] = round((dwell_pivot['On Time'] / dwell_pivot['Grand Total']) * 100, 2)

    # Display Pivot Table
    st.subheader("YTD Count by Dwell Time")
    st.table(dwell_pivot)

    # Add Stacked Bar Chart in Expander
    with st.expander("YTD 100% Stacked Bar Chart: Late vs On Time by Dwell Time Category"):
        categories = dwell_pivot['Dwell Time Category']
        late_percentages = dwell_pivot['Late % of Total'].fillna(0)
        on_time_percentages = dwell_pivot['On Time % of Total'].fillna(0)

        # Create Stacked Bar Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=categories,
            y=on_time_percentages,
            name='On Time',
            marker_color='green',
            text=on_time_percentages,
            textposition='inside'
        ))
        fig.add_trace(go.Bar(
            x=categories,
            y=late_percentages,
            name='Late',
            marker_color='red',
            text=late_percentages,
            textposition='inside'
        ))

        # Layout adjustments
        fig.update_layout(
            barmode='stack',
            title='YTD 100% Stacked Bar Chart: Late vs On Time by Dwell Time Category',
            xaxis_title='Dwell Time Category',
            yaxis_title='% of Total Shipments',
            legend_title='Compliance',
            xaxis_tickangle=-45
        )

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

    # Pivot Table for Average Dwell Time by Visit Type
    dwell_average_pivot = compliance_data.pivot_table(
        values='Dwell Time',
        index='Visit Type',
        columns='Compliance',
        aggfunc='mean',
        fill_value=np.nan
    ).reset_index()

    # Ensure required columns are present
    for col in ['Late', 'On Time']:
        if col not in dwell_average_pivot.columns:
            dwell_average_pivot[col] = 0

    # Add Grand Average
    dwell_average_pivot['Grand Average'] = dwell_average_pivot.select_dtypes(include=[np.number]).mean(axis=1)

    # Add Overall Grand Average Row
    grand_avg_row = dwell_average_pivot.select_dtypes(include=[np.number]).mean().to_frame().T
    grand_avg_row['Visit Type'] = 'Grand Average'
    dwell_average_pivot = pd.concat([dwell_average_pivot, grand_avg_row], ignore_index=True)

    # Display Pivot Table
    st.subheader("YTD Average Dwell Time by Visit Type")
    st.table(dwell_average_pivot)

    # Grouped Bar Chart in Expander
    with st.expander("YTD Average Dwell Time Grouped Bar Chart by Visit Type"):
        fig = go.Figure()

        # Add bars for Late and On Time
        fig.add_trace(go.Bar(
            x=dwell_average_pivot['Visit Type'],
            y=dwell_average_pivot['Late'],
            name='Late',
            marker_color='red',
            text=dwell_average_pivot['Late'],
            textposition='auto',
            texttemplate='%{text:.2f}'
        ))
        fig.add_trace(go.Bar(
            x=dwell_average_pivot['Visit Type'],
            y=dwell_average_pivot['On Time'],
            name='On Time',
            marker_color='green',
            text=dwell_average_pivot['On Time'],
            textposition='auto',
            texttemplate='%{text:.2f}'
        ))

        # Layout adjustments
        fig.update_layout(
            barmode='group',
            title='YTD Average Dwell Time by Visit Type and Compliance',
            xaxis_title='Visit Type',
            yaxis_title='Average Dwell Time (hours)',
            legend_title='Compliance',
            xaxis_tickangle=-45
        )

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

    # Create Excel File
    def to_excel():
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            compliance_pivot.to_excel(writer, sheet_name='On Time by Year', index=False)
            carrier_pivot.to_excel(writer, sheet_name='On Time by Carrier', index=False)
            dwell_pivot.to_excel(writer, sheet_name='Dwell Time Count', index=False)
            dwell_average_pivot.to_excel(writer, sheet_name='Avg Dwell by Visit Type', index=False)
        return output.getvalue()

    # Download Button
    st.download_button(
        label="Download YTD Pivot Tables as Excel",
        data=to_excel(),
        file_name="ytd_pivot_tables.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
