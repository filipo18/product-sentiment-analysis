"""Streamlit dashboard for real-time social sensing."""
from __future__ import annotations

import asyncio
import os
from typing import List

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def fetch_json(path: str, method: str = "GET", payload: dict | None = None):
    url = f"{API_URL}{path}"
    if method == "POST":
        response = requests.post(url, json=payload, timeout=60)
    else:
        response = requests.get(url, params=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def load_metrics(products: List[str]) -> dict:
    params = {"products": products}
    return fetch_json("/metrics", payload=params)


def load_summary(products: List[str]):
    params = {"products": products}
    return fetch_json("/summary", payload=params)


def semantic_search(query: str, limit: int = 5):
    params = {"query": query, "limit": limit}
    return fetch_json("/search", payload=params)


def main() -> None:
    st.set_page_config(page_title="Product Social Sensing", layout="wide")
    st.title("Real-time Product Sentiment")

    default_products = ["iPhone 16", "iPhone 17"]
    products_input = st.text_input("Products", value=", ".join(default_products))
    products = [p.strip() for p in products_input.split(",") if p.strip()]
    if not products:
        st.warning("Enter at least one product")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Discover Sources"):
            with st.spinner("Discovering sources..."):
                discovery = fetch_json("/discover", method="POST", payload={"products": products})
                st.session_state["discovery"] = discovery
    with col2:
        if st.button("Run Ingestion"):
            with st.spinner("Triggering ingestion..."):
                fetch_json(
                    "/ingest",
                    method="POST",
                    payload={"products": products, "sources": []},
                )
                st.success("Ingestion triggered")

    discovery = st.session_state.get("discovery")
    if discovery:
        st.subheader("Discovered Sources")
        for platform, items in discovery.items():
            st.write(platform.upper())
            st.dataframe(pd.DataFrame(items))

    st.subheader("Sentiment Metrics")
    try:
        metrics = load_metrics(products)
        st.json(metrics)
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to load metrics: {exc}")

    st.subheader("Summaries")
    try:
        summaries = load_summary(products)
        for summary in summaries:
            st.markdown(f"### {summary['product']}")
            st.write(summary["overall"])
            col1, col2 = st.columns(2)
            with col1:
                st.write("Top delights")
                st.write(summary.get("delights", []))
            with col2:
                st.write("Top pain points")
                st.write(summary.get("pain_points", []))
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to load summaries: {exc}")

    st.subheader("Semantic Search")
    query = st.text_input("Search discussions", value="battery life")
    if st.button("Search") and query:
        try:
            results = semantic_search(query)
            st.table(pd.DataFrame(results))
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Search failed: {exc}")


if __name__ == "__main__":
    main()
