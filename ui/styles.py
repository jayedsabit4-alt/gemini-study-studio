import streamlit as st

def apply_gemini_theme():
    st.markdown(
        """
        <style>
        /* VIEWPORT LOCK & FLUSH ALIGNMENT */
        html, body, [data-testid="stAppViewContainer"], .main {
            overflow-x: hidden !important;
            max-width: 100vw !important;
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 4rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }

        /* FIX SLIDER OVERLAPPING LABELS */
        div[data-baseweb="slider"] {
            margin-top: 10px !important;
            margin-bottom: 25px !important;
        }
        div[data-baseweb="slider"] div {
            font-size: 14px !important;
        }

        /* GEMINI SIDEBAR DRAWER */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                width: 85vw !important;
                min-width: 85vw !important;
                max-width: 85vw !important;
                background-color: #131314 !important;
            }
        }

        /* SIDEBAR BUTTONS */
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 12px !important;
            background-color: #1e1f20 !important;
            border: 1px solid #2e2f31 !important;
            color: #e3e3e3 !important;
            padding: 6px 12px !important;
            width: 100% !important;
        }

        /* FORMULA RENDERING & TEXT WRAPPING */
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
