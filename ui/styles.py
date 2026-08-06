import streamlit as st

def apply_gemini_theme():
    st.markdown(
        """
        <style>
        /* VIEWPORT LOCK & FLUSH LEFT ALIGNMENT */
        html, body, [data-testid="stAppViewContainer"], .main {
            overflow-x: hidden !important;
            max-width: 100vw !important;
        }

        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }

        /* GEMINI MOBILE DRAWER (85% Screen Width) */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                width: 85vw !important;
                min-width: 85vw !important;
                max-width: 85vw !important;
                background-color: #131314 !important;
            }
        }

        /* SIDEBAR THREAD ROW INLINE ALIGNMENT */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            width: 100% !important;
            gap: 4px !important;
            margin-bottom: 4px !important;
        }

        [data-testid="stSidebar"] [data-testid="column"]:first-child {
            flex: 1 1 80% !important;
            min-width: 0 !important;
        }

        [data-testid="stSidebar"] [data-testid="column"]:last-child {
            flex: 0 0 38px !important;
            min-width: 38px !important;
        }

        [data-testid="stSidebar"] .stButton > button {
            border-radius: 20px !important;
            background-color: #1e1f20 !important;
            border: 1px solid #2e2f31 !important;
            color: #e3e3e3 !important;
            text-align: left !important;
            padding: 6px 12px !important;
            height: 40px !important;
            width: 100% !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        /* FORMULA RENDERING & TEXT WRAPPING PRESERVATION */
        .katex, .katex * {
            white-space: nowrap !important;
        }
        p, li, h1, h2, h3 {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 99999 !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
