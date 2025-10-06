📈 Streamlit Curve Data ExtractorThis web application allows users to upload an image of a graph, define its axis limits, and automatically extract the data points from a curve. The extracted data can be visualized in a plot and downloaded as a CSV file.This tool is useful for digitizing data from scanned plots, academic papers, or legacy reports.FeaturesImage Upload: Supports various image formats (.png, .jpg, .jpeg).Interactive Axis Definition: Simple number inputs to define the graph's X and Y axis ranges.Automatic Curve Detection: Uses scikit-image to find the primary curve in the image.Data Visualization: Instantly plots the extracted data points for verification using Matplotlib.CSV Export: Download the extracted numerical data with a single click.InstallationTo run this application locally, first clone the repository and then set up a Python virtual environment.Clone the repository:git clone <your-repository-url>
cd <your-repository-directory>
Create and activate a virtual environment:# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
Install the required dependencies:pip install -r requirements.txt
UsageOnce the dependencies are installed, you can run the application with the following command:streamlit run streamlit_app.py
Your web browser should automatically open with the application running.How It WorksUpload: The user uploads an image of a graph via the sidebar.Define Axes: The user inputs the minimum and maximum values for the X and Y axes in the sidebar.Extract: Upon clicking "Extract Data," the application converts the image to grayscale, applies a binary threshold to isolate the curve, and uses scikit-image's find_contours function to identify the shape of the curve.Scale & Plot: The pixel coordinates of the curve are scaled to the defined axis limits. The resulting data is then plotted for immediate visual feedback.Download: The extracted data can be downloaded as a clean .csv file.
