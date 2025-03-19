import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

import datetime
import pandas as pd
from database import Database
from process_deals import process_deals_sync

# Custom CSS for buttons and layout
st.markdown(
    """
<style>
    .stButton > button {
        padding: 0.1rem 0.3rem;
        font-size: 0.5rem;
        min-height: 0px;
        height: 20px;
        width: auto;
        border: 1px solid #555;
        border-radius: 3px;
        line-height: 1;
        margin: 0;
    }
    .stButton > button:disabled {
        border: 1px solid #999;
        color: #999;
    }
    /* Adjust column padding and margins */
    [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
    }
    [data-testid="column"] > div {
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Add padding specifically for button columns */
    div[data-testid="column"]:has(button) {
        padding-right: 10px !important;
    }
    /* Remove extra padding from checkbox */
    .stCheckbox {
        padding: 0 !important;
        margin: 0 !important;
    }
    .stCheckbox > label {
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Adjust text margins */
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }
    /* Adjust separator line margins */
    hr {
        margin: 0.2rem 0 !important;
    }
    /* Make text more compact */
    .row-widget > div {
        line-height: 1 !important;
        padding: 0 !important;
    }
    /* Style table headers */
    .header-style {
        font-weight: bold;
        white-space: nowrap;
        overflow: visible;
        text-overflow: unset;
        padding-right: 1rem !important;
    }
    /* Action buttons styling - default dark style for Process button */
    .stButton > button {
        padding: 0.2rem 0.8rem !important;
        font-size: 0.4rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        height: auto !important;
        width: auto !important;
        margin: 0 !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        background-color: #2b2b2b !important;  /* Dark background */
        border: 1px solid #555 !important;
        color: #fff !important;
        transition: all 0.3s ease !important;
        white-space: nowrap !important;
        min-width: 50px !important;
    }
    .stButton > button:hover {
        background-color: #3d3d3d !important;  /* Slightly lighter on hover */
        border-color: #fff !important;
    }
    /* Style specifically for delete button */
    .stButton > [kind="secondary"] {
        background-color: #ff4444 !important;
        border-color: #ff4444 !important;
    }
    .stButton > [kind="secondary"]:hover {
        background-color: #cc0000 !important;
        border-color: #cc0000 !important;
    }
    /* Button container styling */
    .button-container {
        display: flex !important;
        gap: 4px !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Custom button positioning */
    .process-button {
        position: absolute;
        left: 1rem;
    }
    .delete-button {
        position: absolute;
        right: 1rem;
    }
    .button-spacer {
        height: 3rem;
        position: relative;
    }
    /* Add margin after the header */
    h1, h2, h3 {
        margin-bottom: 1.5rem !important;
    }
    /* Adjust column margins for buttons */
    [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
    }
    [data-testid="column"] > div {
        padding: 0 !important;
        margin: 0 !important;
        display: inline-block !important;
    }
    /* Button container styling */
    div[data-testid="column"] > div > div > div > div > button {
        margin-right: 5px !important;
    }
    /* Action buttons container */
    .button-group {
        display: flex !important;
        align-items: center !important;
        gap: 5px !important;
    }
    .button-group > div {
        display: inline-block !important;
    }
    .button-group .stButton {
        margin: 0 !important;
        display: inline-block !important;
    }
    .button-group > div > div {
        display: inline-block !important;
    }
    .button-group .element-container {
        display: inline-block !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize database connection in session state
if "db" not in st.session_state:
    st.session_state.db = Database()  # Database will connect on initialization

# Use session state db throughout the app
db = st.session_state.db

# Initialize processing state in session state if not exists
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# Add date and time selection to sidebar
with st.sidebar:
    st.header("Date and Time Selection")

    # Date picker
    selected_date = st.date_input("Select a date")

    # Time selection
    start_time = st.time_input("Start time", value=datetime.time(0, 0, 0))
    end_time = st.time_input("End time", value=datetime.time(23, 59, 59))

    # Display selected date and time range
    if start_time and end_time:
        if start_time < end_time:
            st.success(
                f'Selected time range: {start_time.strftime("%I:%M %p")} to {end_time.strftime("%I:%M %p")} on {selected_date.strftime("%B %d, %Y")}'
            )

            # Add submit button
            if st.button("Submit"):
                # Insert data into database
                if db.insert_deal_task(selected_date, start_time, end_time):
                    st.success("Task saved successfully!")
                else:
                    st.error("Error saving task to database")
        else:
            st.error("Error: End time must be after start time")

# Main content area - Display deals table
st.header("Deal Tasks")

# Get all deal tasks
deal_tasks = db.get_all_deal_tasks()

if deal_tasks:
    # Create DataFrame
    df = pd.DataFrame(
        deal_tasks, columns=["ID", "Date", "Start Time", "End Time", "Status"]
    )

    # Display table header
    cols = st.columns([1, 2, 2, 2, 1.5])
    with cols[0]:
        st.write("Select")
    with cols[1]:
        st.write("Date")
    with cols[2]:
        st.write("Start Time")
    with cols[3]:
        st.write("End Time")
    with cols[4]:
        st.write("Status")

    st.markdown("---")

    # Initialize selected_rows in session state if not exists
    if "selected_rows" not in st.session_state:
        st.session_state.selected_rows = {}

    # Display rows with checkboxes
    for idx, row in df.iterrows():
        cols = st.columns([1, 2, 2, 2, 1.5])

        # Checkbox column
        with cols[0]:
            # Convert date string to datetime.date object
            deal_date = datetime.datetime.strptime(row["Date"], "%Y-%m-%d").date()
            today = datetime.date.today()

            # Determine if checkbox should be disabled
            is_old_date = deal_date < today
            is_success = row["Status"] == "success"
            should_disable = (
                is_success and is_old_date
            )  # Only disable if both old AND success

            # Set help text based on condition
            help_text = None
            if is_old_date and is_success:
                help_text = "Cannot process: Past successful deal"
            elif is_success and deal_date == today:
                help_text = "Can be reprocessed today"
            elif is_old_date:
                help_text = "Processing past date"

            is_checked = st.checkbox(
                f"Select deal {row['ID']}",
                key=f"checkbox_{row['ID']}",
                label_visibility="collapsed",
                disabled=should_disable,
                help=help_text,
            )
            st.session_state.selected_rows[row["ID"]] = is_checked

        # Data columns
        with cols[1]:
            st.write(row["Date"])
        with cols[2]:
            st.write(row["Start Time"])
        with cols[3]:
            st.write(row["End Time"])
        with cols[4]:
            st.write(row["Status"])

    st.markdown("---")

    # Get selected deal IDs
    selected_ids = [
        id for id, is_selected in st.session_state.selected_rows.items() if is_selected
    ]

    if selected_ids:
        col1, _ = st.columns([3, 9])
        with col1:
            c1, gap, c2 = st.columns([0.95, 0.1, 0.95])
            with c1:
                # Process button with loading state
                process_button = st.button(
                    "Process",
                    key="process_selected",
                    disabled=st.session_state.is_processing,
                )

                if process_button:
                    st.session_state.is_processing = True
                    try:
                        with st.spinner("Processing deals..."):
                            # Prepare list of dictionaries for selected deals
                            deals_to_process = []
                            for deal_id in selected_ids:
                                # Get the filtered DataFrame and check if it's not empty
                                filtered_df = df[df["ID"] == deal_id]
                                if not filtered_df.empty:
                                    deal_row = filtered_df.iloc[0]
                                    deals_to_process.append(
                                        {
                                            "id": int(deal_id),
                                            "start_datetime": datetime.datetime.strptime(
                                                f"{deal_row['Date']} {deal_row['Start Time']}",
                                                "%Y-%m-%d %H:%M:%S",
                                            ),
                                            "end_datetime": datetime.datetime.strptime(
                                                f"{deal_row['Date']} {deal_row['End Time']}",
                                                "%Y-%m-%d %H:%M:%S",
                                            ),
                                            "status": deal_row["Status"],
                                        }
                                    )
                                else:
                                    st.error(f"Deal {deal_id} not found in the table")
                                    continue

                            # Call the process_deals function only if we have deals to process
                            if deals_to_process:
                                success = process_deals_sync(deals_to_process)
                                if success:
                                    st.success("All deals processed successfully!")
                                else:
                                    st.warning(
                                        "Some deals failed to process. Check the logs for details."
                                    )
                            else:
                                st.warning("No valid deals selected for processing")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    finally:
                        st.session_state.is_processing = False
                        st.rerun()

            with c2:
                # Delete button with loading state
                delete_button = st.button(
                    "Delete",
                    key="delete_selected",
                    type="secondary",
                    disabled=st.session_state.is_processing,
                )

                if delete_button:
                    st.session_state.is_processing = True
                    with st.spinner("Deleting deals..."):
                        for deal_id in selected_ids:
                            if db.delete_deal(deal_id):
                                st.success(f"Deal {deal_id} deleted successfully!")
                            else:
                                st.error(f"Failed to delete Deal {deal_id}")

                        st.session_state.is_processing = False
                        st.rerun()

else:
    st.info("No deal tasks have been added yet.")
