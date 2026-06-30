import streamlit as st

from core.persistence import save_draft_order


def render():
    st.header("Game Version")
    st.write("Set the draft sequence for your current game version.")

    st.caption("Current sequence")
    st.write(
        " → ".join(
            f"{'🔵' if side == 'blue' else '🔴'} {side.title()} {action}"
            for side, action in st.session_state.draft_order
        )
    )

    if "draft_order_buffer" not in st.session_state:
        if st.button("Set draft order", type="primary"):
            st.session_state.draft_order_buffer = []
            st.rerun()
        return

    st.subheader("Build draft order")
    st.caption("Add each action in the order it occurs.")

    action_buttons = st.columns(4)
    available_actions = [
        ("blue", "Pick"),
        ("blue", "Ban"),
        ("red", "Pick"),
        ("red", "Ban"),
    ]

    for column, (side, action) in zip(
        action_buttons,
        available_actions,
        strict=True,
    ):
        side_marker = "🔵" if side == "blue" else "🔴"
        with column:
            if st.button(
                f"{side_marker} {side.title()} {action}",
                width="stretch",
                key=f"add_{side}_{action}",
            ):
                st.session_state.draft_order_buffer.append((side, action))
                st.rerun()

    draft_order_buffer = st.session_state.draft_order_buffer
    if draft_order_buffer:
        st.write(
            " → ".join(
                f"{'🔵' if side == 'blue' else '🔴'} {side.title()} {action}"
                for side, action in draft_order_buffer
            )
        )
    else:
        st.info("No actions added yet.")

    controls = st.columns(4)
    with controls[0]:
        if st.button("Undo last", disabled=not draft_order_buffer, width="stretch"):
            draft_order_buffer.pop()
            st.rerun()
    with controls[1]:
        if st.button("Clear", disabled=not draft_order_buffer, width="stretch"):
            draft_order_buffer.clear()
            st.rerun()
    with controls[2]:
        if st.button("Cancel", width="stretch"):
            del st.session_state.draft_order_buffer
            st.rerun()
    with controls[3]:
        if st.button(
            "Save",
            type="primary",
            disabled=not draft_order_buffer,
            width="stretch",
        ):
            st.session_state.draft_order = draft_order_buffer.copy()
            save_draft_order(st.session_state.draft_order)
            del st.session_state.draft_order_buffer
            st.success("Draft order saved.")
            st.rerun()


render()
