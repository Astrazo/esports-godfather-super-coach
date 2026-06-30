import streamlit as st

from core.persistence import save_coach_messages
from core.runtime import load_game


def render():
    _, _, agent = load_game()

    st.header("Coach")
    st.caption("Ask about heroes, builds, attributes, game terms, or team compositions.")

    if st.button("Clear conversation", disabled=not st.session_state.coach_messages):
        st.session_state.coach_messages = []
        save_coach_messages(st.session_state.coach_messages)
        st.rerun()

    for message in st.session_state.coach_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask your coach their thoughts on Babe...")
    if not prompt:
        return

    st.session_state.coach_messages.append({"role": "user", "content": prompt})
    save_coach_messages(st.session_state.coach_messages)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                stream = agent.stream_events(
                    {"messages": st.session_state.coach_messages},
                    version="v3",
                )
                response_parts = []
                response_placeholder = st.empty()

                for kind, item in stream.interleave("messages", "tool_calls"):
                    if kind == "messages":
                        for token in item.text:
                            response_parts.append(token)
                            response_placeholder.markdown("".join(response_parts) + " ▌")
                    elif kind == "tool_calls":
                        response_parts.append(f"{item.tool_name}({item.input})")
                        response_placeholder.markdown("".join(response_parts) + " ▌")
              
                response = "".join(response_parts)
                response_placeholder.markdown(response)
            except Exception as error:
                st.error(f"The coach could not respond: {error}")
                return

    st.session_state.coach_messages.append({"role": "assistant", "content": response})
    save_coach_messages(st.session_state.coach_messages)


render()
