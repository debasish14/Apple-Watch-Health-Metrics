# ⌚ Apple Watch Health Metrics

A full-stack application and data analysis toolkit designed to process, analyze, and visualize your personal Apple Health data exports. Turn your raw XML watch data into actionable insights and beautiful visualizations!

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Backend-green.svg)

---

## ✨ Features

- **Automated XML Parsing**: Converts heavy Apple Health `export.xml` files into optimized, readable `.csv` datasets.
- **Advanced Python Analysis**: Standalone scripts to conduct deep dives into your health trends (workouts, heart rate, body mass).
- **Interactive Web Dashboard**:
  - **React + Vite Frontend**: Rapid and responsive web UI built with Tailwind CSS.
  - **Recharts Integrations**: Beautiful, dynamic graphs displaying your health and workout metrics.
  - **Flask Backend**: Processes uploaded files and serves health data through robust APIs.
- **Privacy First**: All data is processed locally. Your personal `.csv` and `.xml` datasets never leave your machine (unless you choose otherwise).

---

## 🏗️ Project Structure

```bash
Apple Watch Health Metrics/
├── backend/                  # Flask REST API handling data processing & uploads
├── frontend/                 # Vite + React web application with Tailwind
├── apple_health_export/      # 🚫 Your raw Apple Health export.xml (ignored by git)
├── output_plots/             # 🚫 Generated charts from python offline scripts (ignored by git)
├── analyze_health_data.py    # Offline python analytics script
├── advanced_insights_analysis.py # Deep learning / advanced metric extraction script
└── xml_to_csv.py             # Script to parse export.xml into CSVs
```

---

## 🚀 Getting Started

To run this project on your local machine, you'll need to set up both the backend server and the frontend development server.

### 1. Prerequisites
- Python 3.8+
- Node.js (v16+ recommended)
- An Apple Health export (Go to Health App on iPhone -> Profile -> Export All Health Data)

### 2. Setting up the Backend (Flask)

1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Flask server:
   ```bash
   python app.py
   ```
   *The backend will typically run on `http://127.0.0.1:5000`.*

### 3. Setting up the Frontend (React + Vite)

1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install the Node modules:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend will be available at `http://localhost:5173` (or the port specified in your terminal).*

---

## 📊 Using the Standalone Python Scripts

If you just want to analyze your data offline using Python (without the web UI):

1. Make sure you are in the project root directory.
2. Unzip your Apple Health data and place the `export.xml` file inside an `apple_health_export/` folder.
3. Install the root python dependencies (pandas, matplotlib, etc.):
   ```bash
   pip install -r requirements.txt
   ```
4. Run the parser to generate your CSVs:
   ```bash
   python xml_to_csv.py
   ```
5. Run the analytics scripts to generate plots and insights:
   ```bash
   python analyze_health_data.py
   python advanced_insights_analysis.py
   ```

---

## 🛡️ Privacy Notice

**Do NOT commit your personal health data to a public repository!** 
A `.gitignore` file has been pre-configured to automatically exclude `*.csv`, `*.xml`, `node_modules/`, Python environments, and auto-generated plots. Verify your `git status` before pushing to ensure personal payload folders (like `apple_health_export/` and `health_records.csv`) remain local.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
