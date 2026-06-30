import streamlit as st


def enable_page_scroll_over_inputs():
    st.html(
        """
        <script>
        const listenerKey = "__lazyGodfatherInputWheelScroll";

        if (!window[listenerKey]) {
            document.addEventListener(
                "wheel",
                (event) => {
                    if (event.ctrlKey) {
                        return;
                    }

                    const target = event.target;
                    const input = target.closest?.(
                        'input, textarea, [role="combobox"], ' +
                        '[data-testid="stNumberInput"], ' +
                        '[data-testid="stTextInput"], ' +
                        '[data-testid="stSelectbox"]'
                    );

                    if (!input || target.closest?.('[role="listbox"]')) {
                        return;
                    }

                    event.preventDefault();
                    const scrollContainer = document.querySelector(
                        '[data-testid="stMain"]'
                    );

                    if (scrollContainer) {
                        scrollContainer.scrollBy(event.deltaX, event.deltaY);
                    } else {
                        window.scrollBy(event.deltaX, event.deltaY);
                    }
                },
                { capture: true, passive: false }
            );
            window[listenerKey] = true;
        }
        </script>
        """,
        unsafe_allow_javascript=True,
    )
