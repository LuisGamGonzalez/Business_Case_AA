# ATD Dashboard (Streamlit)

This Streamlit application provides an analytical dashboard focused on **ATD (Average Time to Deliver)** and **Trips** performance metrics.  
It enables users to visualize delivery trends, segment operational data, and derive insights for performance optimization.

Link: https://michelangelo-studio.uberinternal.com/session/34a0c718-4896-415e-9329-e748ae12d51a/phoenix/dashboard/eb4545ff-4a77-4ae5-bcde-8ada05c9e4ad/

Dataset: https://drive.google.com/drive/folders/1xr3vW18isv3Pjo9OgSE5DQYF_8qi92of?usp=sharing

---

## 🚀 Overview

The dashboard includes:

### **KPIs**
- **Trips**: Total number of deliveries.
- **ATD Mean / Median / P90**: Core delivery time performance metrics.

### **Visuals**
- **Daily trend**: Dual-axis line chart — ATD (left, 🟩 green) and Trips (right, 🟨 yellow).
- **Business segmentations**:
  - Territory  
  - Geo Archetype  
  - Courier Flow  
  - Merchant Surface
- **Temporal breakdowns**:
  - Day of week (Mon → Sun)  
  - Hour of day (0 → 23)  
  - Weekend vs Weekday
- **Distance analysis**:
  - Scatter plot — Pickup vs Dropoff distance (bubble size = ATD).
- **Distribution analysis**:
  - Histogram — ATD (X) vs Trips (Y).

---

## 🧭 Sidebar Controls

### **Mode selector**
- **Tutorial**: Displays a guide explaining metrics, color meanings, and filter usage.  
- **Dashboard**: Displays all filters, KPIs, and visualizations.

### **Dataset selector**
The app supports two datasets (configured in `app.py`):

```python
DATA_SOURCES = {
    "Data Complete": "/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_complete.csv",
    "Data without outliers": "/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_without_outliers.csv",
}
```

Select:
- **Data Complete** — full dataset.
- **Data without outliers** — cleaned dataset with extreme values removed.

### **Filters (available in Dashboard mode)**
- **Territory**
- **Geo archetype**
- **Courier flow**
- **Merchant surface**
- **Date range (Eater request)**
- **Pickup distance** range
- **Dropoff distance** range

All charts and KPIs update dynamically according to the active filters.

---

## 🎨 Color Legend

| Metric | Color | Description |
|--------|--------|-------------|
| **ATD** | 🟩 `#03c167` | Average Time to Deliver (minutes) |
| **Trips** | 🟨 `#ffc043` | Number of completed deliveries |

---

## ⚙️ Setup Instructions & Quickstart

This section explains how to set up, configure, and run the ATD Dashboard on any machine — ensuring full reproducibility and consistency across environments.

---

### **1️⃣ Clone or download the repository**
Clone this project from GitHub (or copy the source folder into your working directory):

```bash
git clone https://github.com/LuisGamGonzalez/Business_Case_AA.git
cd streamlit-atd-dashboard
```

If this is being deployed in a production or shared environment, ensure the repository has the same structure as described in the **Project Structure** section below.

---

### **2️⃣ Create and activate a Python virtual environment**
It is recommended to isolate dependencies using a virtual environment to prevent conflicts with global packages.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

Once activated, your terminal prompt should display `(.venv)` indicating the environment is active.

---

### **3️⃣ Install all required dependencies**
Install the Python libraries specified in the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

If installation takes time, you can check progress with:

```bash
pip list
```

---

### **4️⃣ Verify dependency versions (optional but recommended)**
To ensure reproducibility, verify that the installed package versions match the expected ones:

```bash
python -m pip list | grep -E "streamlit|altair|pandas|numpy|python-dateutil"
```

Expected output:
```
streamlit==1.12.0
pandas==2.1.2
numpy==1.24.0
altair==4.0.0
python-dateutil==2.8.2
```

If any package differs, fix it manually:
```bash
pip install streamlit==1.12.0 altair==4.0.0 pandas==2.1.2 numpy==1.24.0 python-dateutil==2.8.2
```

---

### **5️⃣ Validate dataset paths**
Ensure the following datasets exist in your environment:

```
/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_complete.csv
/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_without_outliers.csv
```

If your data is located elsewhere, update the file paths in the `DATA_SOURCES` dictionary located at the top of `app.py`:

```python
DATA_SOURCES = {
    "Data Complete": "<path_to_data_complete.csv>",
    "Data without outliers": "<path_to_data_without_outliers.csv>",
}
```

---

### **6️⃣ Run the Streamlit app**
Start the dashboard locally by executing:

```bash
streamlit run app.py
```

When executed successfully, Streamlit will display a message like:
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://<your_machine_ip>:8501
```


---

## 🧩 Project Structure

```
app.py            # Main Streamlit interface (UI + logic)
utils.py          # Data preparation, metrics, and chart helper functions
requirements.txt  # Python dependencies
.flake8           # Linting configuration (PEP8 + Black compatible)
README.md         # Documentation and setup guide
data_complete.csv # Original Data
data_without_outliers.csv #Data without Outliers
```
