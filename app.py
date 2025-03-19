import streamlit as st

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import datetime
import pandas as pd
from database import Database
from process_deals import process_deals_sync
from delete_deals import delete_deals_sync

# Custom CSS for buttons and layout
st.markdown(
    """
<style>
    /* Basic button styling */
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

    /* Column and layout adjustments */
    [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
    }
    [data-testid="column"] > div {
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="column"]:has(button) {
        padding-right: 10px !important;
    }

    /* Checkbox styling */
    .stCheckbox {
        padding: 0 !important;
        margin: 0 !important;
    }
    .stCheckbox > label {
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Text and layout adjustments */
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }
    hr {
        margin: 0.2rem 0 !important;
    }
    .row-widget > div {
        line-height: 1 !important;
        padding: 0 !important;
    }

    /* Table header styling */
    .header-style {
        font-weight: bold;
        white-space: nowrap;
        overflow: visible;
        text-overflow: unset;
        padding-right: 1rem !important;
    }

    /* Button styling */
    .stButton > button {
        padding: 0.2rem 0.8rem !important;
        font-size: 0.4rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        height: 24px !important;
        width: 120px !important;
        margin: 0 !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        background-color: #2b2b2b !important;
        border: 1px solid #555 !important;
        color: #fff !important;
        transition: all 0.3s ease !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .stButton > button:hover {
        background-color: #3d3d3d !important;
        border-color: #fff !important;
    }

    /* Delete button specific styling */
    .stButton > [kind="secondary"] {
        background-color: #ff4444 !important;
        border-color: #ff4444 !important;
        width: 120px !important;
    }
    .stButton > [kind="secondary"]:hover {
        background-color: #cc0000 !important;
        border-color: #cc0000 !important;
    }

    /* Button layout and spacing */
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
    div[data-testid="column"] > div > div > div > div > button {
        margin-right: 5px !important;
        width: 120px !important;
    }

    /* Header margins */
    h1, h2, h3 {
        margin-bottom: 1.5rem !important;
    }

    /* Button positioning */
    .stButton {
        position: static !important;
        float: none !important;
        display: block !important;
    }

    /* Column spacing */
    div[data-testid="column"]:first-child {
        padding-right: 15px !important;
    }
    div[data-testid="column"]:last-child {
        padding-left: 15px !important;
    }

    /* Disabled button states */
    .stButton > button:disabled {
        opacity: 0.6 !important;
        cursor: not-allowed !important;
        pointer-events: none !important;
    }
    .stButton > button[kind="secondary"]:disabled {
        opacity: 0.6 !important;
        cursor: not-allowed !important;
        pointer-events: none !important;
        background-color: #ff4444 !important;
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

# Initialize all session state variables at the start of the app
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "processing_state" not in st.session_state:
    st.session_state.processing_state = False
if "deleting_state" not in st.session_state:
    st.session_state.deleting_state = False

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
            # Create three columns with even wider gap in middle
            c1, gap, c2 = st.columns([1, 1.5, 1])

            # Initialize button states if not exists
            if "processing_state" not in st.session_state:
                st.session_state.processing_state = False
            if "deleting_state" not in st.session_state:
                st.session_state.deleting_state = False

            # Calculate disabled state
            is_disabled = (
                st.session_state.processing_state or st.session_state.deleting_state
            )

            with c1:
                # Process button
                if st.button(
                    "Processing..." if st.session_state.processing_state else "Process",
                    key="process_selected",
                    disabled=is_disabled,
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.processing_state = True
                    st.rerun()

                # Handle processing
                if st.session_state.processing_state:
                    try:
                        # Prepare list of dictionaries for selected deals
                        deals_to_process = []
                        for deal_id in selected_ids:
                            filtered_df = df[df["ID"] == deal_id]
                            if filtered_df.empty:
                                continue

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

                        if deals_to_process:
                            success, success_ids, failed_ids = process_deals_sync(
                                deals_to_process
                            )

                            # Show a single success message if all processing succeeded
                            if success:
                                st.success(
                                    "All selected deals were processed successfully!"
                                )
                            else:
                                # Show summary messages for partial success/failure
                                if success_ids:
                                    st.success(
                                        f"Successfully processed {len(success_ids)} deals"
                                    )
                                if failed_ids:
                                    st.error(
                                        f"Failed to process {len(failed_ids)} deals: {', '.join(map(str, failed_ids))}"
                                    )
                        else:
                            st.warning("No valid deals selected for processing")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    finally:
                        st.session_state.processing_state = False
                        st.rerun()

            # Add visual gap
            with gap:
                st.write("")

            with c2:
                # Delete button
                if st.button(
                    "Deleting..." if st.session_state.deleting_state else "Delete",
                    key="delete_selected",
                    disabled=is_disabled,
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.deleting_state = True
                    st.rerun()

                # Handle deletion
                if st.session_state.deleting_state:
                    try:
                        success, success_ids, failed_ids = delete_deals_sync(
                            selected_ids
                        )

                        # Show a single success message if all deletions succeeded
                        if success:
                            st.success("All selected deals were deleted successfully!")
                        else:
                            # Show summary messages for partial success/failure
                            if success_ids:
                                st.success(
                                    f"Successfully deleted {len(success_ids)} deals"
                                )
                            if failed_ids:
                                st.error(
                                    f"Failed to delete {len(failed_ids)} deals: {', '.join(map(str, failed_ids))}"
                                )
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                    finally:
                        st.session_state.deleting_state = False
                        st.rerun()

else:
    st.info("No deal tasks have been added yet.")
