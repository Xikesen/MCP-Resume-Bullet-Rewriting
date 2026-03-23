import os
import requests
import streamlit as st

API_BASE = os.getenv(
    "MCP_CLIENT_API_URL",
    "http://localhost:8000"
).rstrip("/")

st.title("Scalable LangGraph RAG Application")

prompt = st.text_input("Ask")

if st.button("Send") and prompt:
    payload = {"query": prompt}
        
    r = requests.post(
        f"{API_BASE}/invoke",
        json=payload,
        timeout=200
    )
    r.raise_for_status()

    st.json(r.json())