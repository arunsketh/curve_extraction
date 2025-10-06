import streamlit as st
import pandas as pd
import tempfile
import subprocess
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="PlotDigitizer Streamlit", layout="wide")
st.title("Digitize a plot with PlotDigitizer")

uploaded = st.file_uploader("Upload a plot image (PNG/JPG)", type=["png", "jpg", "jpeg"])
if uploaded:
    # Load and show image
    image = Image.open(uploaded).convert("RGB")
    w, h = image.size
    st.write(f"Image size: {w} x {h}")

    # Inputs for world-axis points (-p)
    st.subheader("Axis reference points (-p)")
    c1, c2, c3 = st.columns(3)
    with c1:
        p1x = st.number_input("P1 x (e.g., 0)", value=0.0, step=1.0, format="%.6f")
        p1y = st.number_input("P1 y (e.g., 0)", value=0.0, step=1.0, format="%.6f")
    with c2:
        p2x = st.number_input("P2 x (e.g., 10)", value=10.0, step=1.0, format="%.6f")
        p2y = st.number_input("P2 y (e.g., 0)", value=0.0, step=1.0, format="%.6f")
    with c3:
        p3x = st.number_input("P3 x (e.g., 0)", value=0.0, step=1.0, format="%.6f")
        p3y = st.number_input("P3 y (e.g., 1)", value=1.0, step=1.0, format="%.6f")

    st.caption("Click the image below to pick matching pixel positions (-l) for P1, P2, P3 in the same order.")

    # Maintain click list in session
    if "clicks" not in st.session_state:
        st.session_state.clicks = []

    # Display image and capture clicks
    click = streamlit_image_coordinates(image, key="img_clicks")
    if click is not None:
        # Store only when a new timestamp arrives
        ts = click.get("time")
        if "last_ts" not in st.session_state or st.session_state.last_ts != ts:
            st.session_state.last_ts = ts
            st.session_state.clicks.append((int(click["x"]), int(click["y"])))

    # Show collected clicks and offer reset
    st.write(f"Collected clicks (x,y) in order: {st.session_state.clicks}")
    if st.button("Reset clicks"):
        st.session_state.clicks = []

    # Run when 3 clicks collected (adapt to 4 if origin not visible)
    if len(st.session_state.clicks) == 3:
        # Convert top-left-origin y to bottom-left-origin row for PlotDigitizer
        # PlotDigitizer expects (row,column) with (0,0) at bottom-left per its docs
        L_points = []
        for x_tl, y_tl in st.session_state.clicks:
            row_bl = h - 1 - y_tl
            col = x_tl
            L_points.append((row_bl, col))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
            image.save(tmp_img.name)

            cmd = [
                "plotdigitizer",
                tmp_img.name,
                "-p", f"{p1x},{p1y}",
                "-p", f"{p2x},{p2y}",
                "-p", f"{p3x},{p3y}",
                "-l", f"{L_points[0][0]},{L_points[0][1]}",
                "-l", f"{L_points[1][0]},{L_points[1][1]}",
                "-l", f"{L_points[2][0]},{L_points[2][1]}",
                "--output", tmp_csv.name,
            ]

            st.code(" ".join(cmd))
            with st.spinner("Running PlotDigitizer..."):
                result = subprocess.run(cmd, capture_output=True, text=True)

            st.subheader("CLI output")
            st.text(result.stdout or "(no stdout)")
            st.text(result.stderr or "(no stderr)")

            # Load and show CSV
            try:
                df = pd.read_csv(tmp_csv.name)
                st.subheader("Extracted data")
                st.dataframe(df)
                st.download_button("Download CSV", df.to_csv(index=False), "digitized.csv", "text/csv")
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
