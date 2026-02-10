# LLM Benchmark Viewer

A clean single-page application to visualize and aggregate LLM benchmark results.

## Features
- **Host View**: Analyze performance per host with hardware details.
- **Model View**: Compare model performance across different hardware configurations.
- **Global Aggregation**: Aggregate by GPU, Model Family, OS, or Specific Model.
- **Statistical Analysis**: Shows Mean, Median, and Coefficient of Variation for all metrics.

## Getting Started

1.  **Install dependencies**:
    ```bash
    npm install
    ```

2.  **Run the development server**:
    ```bash
    npm run dev
    ```

3.  **View the app**:
    Open the URL provided by Vite (usually `http://localhost:5173`).

## Project Structure
- `src/App.jsx`: Main application logic and UI.
- `benchmark_results.json`: The data source (loaded dynamically).
- `tailwind.config.js`: Styling configuration.
