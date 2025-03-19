import streamlit as st

from typing import List, Tuple


def delete_deals_sync(deal_ids: List[int]) -> Tuple[bool, List[int], List[int]]:
    """
    Delete multiple deals synchronously.

    Args:
        deal_ids: List of deal IDs to delete

    Returns:
        Tuple containing:
        - bool: True if all deals were deleted successfully
        - List[int]: Successfully deleted deal IDs
        - List[int]: Failed deal IDs
    """
    try:
        db = st.session_state.db
        success_ids = []
        failed_ids = []

        for deal_id in deal_ids:
            if db.delete_deal(deal_id):
                success_ids.append(deal_id)
            else:
                failed_ids.append(deal_id)

        return len(failed_ids) == 0, success_ids, failed_ids
    except Exception as e:
        return False, [], deal_ids
