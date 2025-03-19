from typing import List
import streamlit as st
from database import Database


def delete_deals_sync(deal_ids: List[int]) -> bool:
    """
    Delete multiple deals synchronously.

    Args:
        deal_ids: List of deal IDs to delete

    Returns:
        bool: True if all deals were deleted successfully, False otherwise
    """
    try:
        db = st.session_state.db
        success = True

        for deal_id in deal_ids:
            if not db.delete_deal(deal_id):
                st.error(f"Failed to delete Deal {deal_id}")
                success = False
            else:
                st.success(f"Deal {deal_id} deleted successfully!")

        return success
    except Exception as e:
        st.error(f"An error occurred while deleting deals: {str(e)}")
        return False
