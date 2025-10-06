import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from skimage.measure import find_contours
import pandas as pd
import io

def extract_curve_data(np_image, x_min, x_max, y_min, y_max):
    """
    Core logic to extract curve data from a numpy image array.
    """
    # Convert to grayscale if the image is in color
    if len(np_image.shape) == 3 and np_image.shape[2] > 1:
        # Handle RGBA images by slicing off the alpha channel
        gray = np.dot(np_image[...,:3], [0.2989, 0.5870, 0.1140])
    else:
        gray = np_image

    # Apply a binary threshold (assumes dark curve on a light background)
    # The threshold value (127) can be adjusted if needed.
    binary = (gray <= 127).astype(np.uint8) * 255
    
    # Find contours using scikit-image
    contours = find_contours(binary, 128)
    
    if not contours:
        return None, None
        
    # Assume the longest contour is the curve of interest
    curve_contour = max(contours, key=len)
    
    # Sort points by their x-coordinate (column 1)
    # scikit-image returns coordinates as (row, col) which corresponds to (y, x)
    sorted_points = curve_contour[curve_contour[:, 1].argsort()]
    
    pixel_x = sorted_points[:, 1]
    pixel_y = sorted_points[:, 0]
    
    img_height, img_width = gray.shape[:2]
    
    # Scale pixel coordinates to data coordinates
    extracted_x = x_min + (pixel_x / img_width) * (x_max - x_min)
    # Invert y-axis scaling because image y=0 is at the top
    extracted_y = y_max - (pixel_y / img_height) * (y_max - y_min)
    
    return extracted_x, extracted_y

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")
st.title("📈 Curve Data Extractor")
st.write("Upload an image of a graph, define the axes, and extract the data points from the curve.")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader("Choose a graph image", type=["png", "jpg", "jpeg", "bmp"])
    
    st.subheader("Define Axis Limits")
    col1, col2 = st.columns(2)
    with col1:
        x_min = st.number_input("X Min", value=0.0, format="%.2f")
        y_min = st.number_input("Y Min", value=0.0, format="%.2f")
    with col2:
        x_max = st.number_input("X Max", value=10.0, format="%.2f")
        y_max = st.number_input("Y Max", value=100.0, format="%.2f")

    extract_button = st.button("Extract Data", type="primary", use_container_width=True)

# --- Main Area for Display ---
col_img, col_plot = st.columns(2)

with col_img:
    st.subheader("Image Preview")
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Graph", use_column_width=True)
    else:
        st.info("Please upload an image using the sidebar control.")

with col_plot:
    st.subheader("Extracted Data Plot")
    # Use a placeholder for the plot area
    plot_container = st.empty()
    plot_container.info("The plot of the extracted data will appear here.")


# --- Processing and Logic ---
if extract_button and uploaded_file:
    with st.spinner("Processing image..."):
        try:
            # Convert uploaded file to numpy array
            pil_image = Image.open(uploaded_file)
            np_image = np.array(pil_image)

            # Perform data extraction
            x_data, y_data = extract_curve_data(np_image, x_min, x_max, y_min, y_max)

            if x_data is not None and y_data is not None:
                st.session_state['x_data'] = x_data
                st.session_state['y_data'] = y_data
                
                # Plot the results
                fig, ax = plt.subplots()
                ax.plot(x_data, y_data, 'r.-', label='Extracted Data')
                ax.set_title("Extracted Data Preview")
                ax.set_xlabel("X-Axis")
                ax.set_ylabel("Y-Axis")
                ax.grid(True)
                ax.legend()
                plot_container.pyplot(fig)
                
                st.toast(f"Successfully extracted {len(x_data)} data points!", icon="✅")
                
            else:
                st.error("No curve could be found in the image. Please check the image contrast or ensure the curve is continuous.")
                st.session_state['x_data'] = None
                st.session_state['y_data'] = None

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            st.session_state['x_data'] = None
            st.session_state['y_data'] = None

# Add download button in the sidebar if data exists
if 'x_data' in st.session_state and st.session_state['x_data'] is not None:
    with st.sidebar:
        st.subheader("Download Data")
        df = pd.DataFrame({
            'x_value': st.session_state['x_data'],
            'y_value': st.session_state['y_data']
        })
        
        # Convert dataframe to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        st.download_button(
            label="Download as CSV",
            data=csv_buffer.getvalue(),
            file_name="extracted_data.csv",
            mime="text/csv",
            use_container_width=True
        )
