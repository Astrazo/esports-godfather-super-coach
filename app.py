import streamlit as st

from core.runtime import initialise_session, load_game
from core.ui import enable_page_scroll_over_inputs


def main():
    st.set_page_config(
        page_title="Lazy Esports Godfather",
        page_icon="🎮",
        layout="wide",
    )
    enable_page_scroll_over_inputs()

    _, default_graph, _ = load_game()
    initialise_session(default_graph)
    st.sidebar.title("Lazy Esports Godfather")
    pages = {
        "Team": [
            st.Page("screens/coach.py", title="Coach", icon=":material/chat:"),
            st.Page("screens/my_team.py", title="My Team", icon=":material/groups:"),
        ],
        "Strategy": [
            st.Page(
                "screens/master_graph.py",
                title="Master Graph",
                icon=":material/hub:",
            ),
            st.Page(
                "screens/game_version.py",
                title="Game Version",
                icon=":material/tune:",
            ),
            st.Page(
                "screens/draft.py",
                title="Start Draft",
                icon=":material/sports_esports:",
            ),
        ],
    }

    
    selected_page = st.navigation(pages)
    selected_page.run()


if __name__ == "__main__":
    main()
