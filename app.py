import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from skimage.measure import find_contours
import pandas as pd
import io
from streamlit_image_coordinates import streamlit_image_coordinates

# --- Core Logic ---

def scale_point(px, py, calibration_points):
    """
    Scales a single pixel coordinate to a data coordinate using the
    4-point calibration data.
    """
    # Pixel coordinates from calibration
    p_x1, p_y1 = calibration_points['X1']['pixel']
    p_x2, p_y2 = calibration_points['X2']['pixel']
    p_x3, p_y3 = calibration_points['Y1']['pixel']
    p_x4, p_y4 = calibration_points['Y2']['pixel']

    # Data values from calibration
    d_x1 = calibration_points['X1']['value']
    d_x2 = calibration_points['X2']['value']
    d_y1 = calibration_points['Y1']['value']
    d_y2 = calibration_points['Y2']['value']

    # Linear interpolation for X
    # Assumes X-axis is mostly horizontal
    data_x = d_x1 + (px - p_x1) * (d_x2 - d_x1) / (p_x2 - p_x1)
    
    # Linear interpolation for Y
    # Assumes Y-axis is mostly vertical, and image y-coordinates increase downwards
    data_y = d_y1 + (py - p_y3) * (d_y2 - d_y1) / (p_y4 - p_y3)

    return data_x, data_y

def extract_curve_data(np_image, calibration_points, threshold_value=127):
    """
    Extracts curve data from an image using scikit-image, then scales it
    using the provided calibration points.
    """
    # 1. Image Preprocessing
    if len(np_image.shape) == 3 and np_image.shape[2] > 1:
        gray = np.dot(np_image[...,:3], [0.2989, 0.5870, 0.1140])
    else:
        gray = np_image
    
    binary = (gray <= threshold_value).astype(np.uint8) * 255
    
    # 2. Contour Detection
    contours = find_contours(binary, 128)
    if not contours:
        return None, None
        
    curve_contour = max(contours, key=len)
    
    # 3. Scaling
    # scikit-image returns (row, col) which is (y, x)
    pixel_y_coords = curve_contour[:, 0]
    pixel_x_coords = curve_contour[:, 1]
    
    scaled_points = [scale_point(px, py, calibration_points) for px, py in zip(pixel_x_coords, pixel_y_coords)]
    
    # 4. Sorting
    scaled_points.sort() # Sort by x-value
    
    extracted_x = np.array([p[0] for p in scaled_points])
    extracted_y = np.array([p[1] for p in scaled_points])
    
    return extracted_x, extracted_y

# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.title("🔬 Web Plot Digitizer")
st.write("A tool inspired by [WebPlotDigitizer](https://automeris.io/WebPlotDigitizer/) to extract data from graph images.")

# --- Session State Initialization ---
if 'calib' not in st.session_state:
    st.session_state.calib = {
        "X1": {"pixel": None, "value": 0.0},
        "X2": {"pixel": None, "value": 1.0},
        "Y1": {"pixel": None, "value": 0.0},
        "Y2": {"pixel": None, "value": 1.0},
    }
if 'image' not in st.session_state:
    st.session_state.image = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

# --- UI Layout ---
col_main, col_sidebar = st.columns([3, 1])

with col_sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader("1. Upload Graph Image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        st.session_state.image = Image.open(uploaded_file)

    if st.session_state.image:
        st.subheader("2. Calibrate Axes")
        st.write("Select a point, enter its value, then click on the image.")
        
        calib_point_select = st.radio(
            "Select calibration point:",
            ("X1", "X2", "Y1", "Y2"),
            horizontal=True,
            key="calib_select"
        )
        
        current_value = st.session_state.calib[calib_point_select]['value']
        new_value = st.number_input(f"Value for {calib_point_select}", value=current_value, key=f"val_{calib_point_select}")
        st.session_state.calib[calib_point_select]['value'] = new_value

        st.info("Current Calibration:")
        st.json(st.session_state.calib)
        
        is_calibrated = all(p['pixel'] is not None for p in st.session_state.calib.values())
        
        st.subheader("3. Extract Data")
        threshold = st.slider("Threshold (for dark line detection)", 0, 255, 127)
        if st.button("Extract Data", type="primary", disabled=not is_calibrated, use_container_width=True):
            with st.spinner("Processing..."):
                x, y = extract_curve_data(np.array(st.session_state.image), st.session_state.calib, threshold)
                if x is not None:
                    st.session_state.extracted_data = {"x": x, "y": y}
                    st.toast(f"Extracted {len(x)} points!", icon="✅")
                else:
                    st.error("No curve found. Try adjusting the threshold.")
                    st.session_state.extracted_data = None
        
        if st.session_state.extracted_data:
            st.subheader("4. Download")
            df = pd.DataFrame(st.session_state.extracted_data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="extracted_data.csv",
                mime="text/csv",
                use_container_width=True
            )

with col_main:
    st.subheader("Image and Plot")
    if st.session_state.image:
        clicked_coords = streamlit_image_coordinates(st.session_state.image, key="image_coords")

        if clicked_coords:
            point_key = st.session_state.calib_select
            st.session_state.calib[point_key]['pixel'] = (clicked_coords['x'], clicked_coords['y'])
            # We use st.rerun() to immediately update the JSON display in the sidebar
            st.rerun()

        if st.session_state.extracted_data:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.imshow(st.session_state.image)
            
            # Convert scaled data back to pixel coordinates to overlay on image
            calib = st.session_state.calib
            p_x1, p_y1, d_x1, d_y1 = calib['X1']['pixel'][0], calib['Y1']['pixel'][1], calib['X1']['value'], calib['Y1']['value']
            p_x2, p_y2, d_x2, d_y2 = calib['X2']['pixel'][0], calib['Y2']['pixel'][1], calib['X2']['value'], calib['Y2']['value']

            plot_x = p_x1 + (st.session_state.extracted_data['x'] - d_x1) * (p_x2 - p_x1) / (d_x2 - d_x1)
            plot_y = p_y1 + (st.session_state.extracted_data['y'] - d_y1) * (p_y2 - p_y1) / (d_y2 - d_y1)

            ax.plot(plot_x, plot_y, 'r-', linewidth=2, label="Extracted Data")
            ax.set_title("Extracted Data Overlay")
            ax.axis('off')
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("After calibrating all 4 points, the extraction result will be shown here.")
            
    else:
        st.info("Upload an image to begin the process.")

