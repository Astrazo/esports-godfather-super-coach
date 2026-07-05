import streamlit as st

from core.persistence import save_coach_messages
from core.runtime import load_game


def render():
    _, _, agent, _, _ = load_game()

    st.header("Coach")
    st.caption("Ask about heroes, builds, attributes, game terms, or team compositions.")

    if st.button("Clear conversation", disabled=not st.session_state.coach_messages):
        st.session_state.coach_messages = []
        save_coach_messages(st.session_state.coach_messages)
        st.rerun()

    # Display current messages in the UI (that aren't tool calls)
    for message in st.session_state.coach_messages:
        if message["role"] == "human":
            with st.chat_message("user"):
                st.markdown(message["content"])

        elif message["role"] == "ai" and not message.get("tool_calls"):
            with st.chat_message("assistant"):
                st.markdown(message["content"])

    # Setup prompt input
    prompt = st.chat_input("What are your thoughts on Babe...")
    if not prompt:
        return

    # Save the new message to the coach messages
    st.session_state.coach_messages.append({"role": "user", "content": prompt})
    save_coach_messages(st.session_state.coach_messages)

    # Append the message to the chat UI
    with st.chat_message("user"):
        st.markdown(prompt)

    # Start the agent response process
    with st.chat_message("ai"):
        with st.spinner("Thinking..."):
            try:
                # Pass in the currnet messages as prompts and get the stream object out
                stream = agent.stream_events(
                    {"messages": st.session_state.coach_messages},
                    version="v3",
                )

                # Initialise response placeholders to help append ai response to chat history
                display_parts = []  # used to keep track of returned tokens
                response_parts = []
                tool_calls = []
                response_placeholder = st.empty()  # what is rendered

                # Interleave messages and tool calls as responses from the AI
                for kind, item in stream.interleave("messages", "tool_calls"):
                    # AI messages
                    if kind == "messages":
                        for token in item.text:
                            # Render
                            display_parts.append(token)
                            response_placeholder.markdown("".join(display_parts) + " ▌")

                            # Append to response parts for later
                            response_parts.append(token)

                    # Tool calls
                    elif kind == "tool_calls":
                        # display_parts.append(f"{item.tool_name}({item.input})")
                        # response_placeholder.markdown("".join(display_parts) + " ▌")

                        tool_calls.append(f"{item.tool_name}({item.input})")

                # Join final AI response
                response = "".join(display_parts)
                response_placeholder.markdown(response)
            except Exception as error:
                st.error(f"The coach could not respond: {error}")
                return
    # Save outputs to file
    outputs = []
    for message in stream.output["messages"]:
        if message.type == "human":
            outputs.append({"role": "human", "content": str(message.text)})
        elif message.type == "ai":
            output = {
                "role": "ai",
                "content": str(message.text),
            }
            if message.tool_calls:
                output["tool_calls"] = [
                    {
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "args": tool_call["args"],
                        "type": "tool_call",
                    }
                    for tool_call in message.tool_calls
                ]
            outputs.append(output)
        elif message.type == "tool":
            outputs.append(
                {
                    "role": "tool",
                    "content": str(message.text),
                    "tool_call_id": message.tool_call_id,
                    "name": message.name,
                }
            )

    st.session_state.coach_messages = outputs
    save_coach_messages(st.session_state.coach_messages)


render()
