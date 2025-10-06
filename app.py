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
    image = Image.open(uploaded).convert("RGB")
    w, h = image.size
    st.write(f"Image size: {w} x {h}")

    # Input axis reference points
    st.subheader("Step 1: Define axis reference points")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Point 1 (Origin or known point)**")
        p1x = st.number_input("X value", value=0.0, key="p1x")
        p1y = st.number_input("Y value", value=0.0, key="p1y")
    
    with col2:
        st.write("**Point 2 (X-axis reference)**")
        p2x = st.number_input("X value", value=10.0, key="p2x")
        p2y = st.number_input("Y value", value=0.0, key="p2y")
    
    with col3:
        st.write("**Point 3 (Y-axis reference)**")
        p3x = st.number_input("X value", value=0.0, key="p3x")
        p3y = st.number_input("Y value", value=1.0, key="p3y")

    st.subheader("Step 2: Click corresponding pixel locations")
    st.caption("Click on the image to mark the pixel locations for Points 1, 2, and 3 in order")

    if "clicks" not in st.session_state:
        st.session_state.clicks = []

    # Display image and capture clicks
    click_data = streamlit_image_coordinates(image, key="calibration")
    
    if click_data is not None:
        x, y = click_data["x"], click_data["y"]
        if len(st.session_state.clicks) < 3:
            st.session_state.clicks.append((x, y))
            st.rerun()

    # Show collected clicks
    for i, (x, y) in enumerate(st.session_state.clicks):
        st.write(f"Point {i+1}: pixel ({x}, {y})")
    
    if st.button("Reset clicks"):
        st.session_state.clicks = []
        st.rerun()

    # Process when all 3 points are collected
    if len(st.session_state.clicks) == 3:
        st.subheader("Step 3: Extract data")
        
        if st.button("Run PlotDigitizer"):
            # Convert coordinates (PlotDigitizer expects row,col from bottom-left)
            pixel_coords = []
            for x, y in st.session_state.clicks:
                row = h - 1 - y  # Convert from top-left to bottom-left origin
                col = x
                pixel_coords.append(f"{row},{col}")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img, \
                 tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
                
                image.save(tmp_img.name)
                
                # Build command with batch mode parameters
                cmd = [
                    "plotdigitizer", 
                    tmp_img.name,
                    "-p", f"{p1x},{p1y}",
                    "-p", f"{p2x},{p2y}", 
                    "-p", f"{p3x},{p3y}",
                    "-l", pixel_coords[0],
                    "-l", pixel_coords[1],
                    "-l", pixel_coords[2],
                    "--output", tmp_csv.name
                ]
                
                with st.spinner("Processing image..."):
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            # Success - load and display results
                            df = pd.read_csv(tmp_csv.name)
                            st.success("Data extraction completed!")
                            st.dataframe(df)
                            
                            # Download button
                            csv_data = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv_data,
                                file_name="extracted_data.csv",
                                mime="text/csv"
                            )
                        else:
                            st.error(f"PlotDigitizer failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        st.error("Process timed out - image may be too complex")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
