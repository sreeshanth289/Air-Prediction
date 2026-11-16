# AirSight — Air Quality Prediction & Pollution Episode Detection

This ZIP contains a browser frontend (HTML/CSS/JavaScript) and a Python API backend. The analysis follows the supplied `air_quality_project.ipynb`: target `CO(GT)`, five PT08 sensor inputs plus T/RH/AH, -200 missing-value handling, hourly interpolation, lag/time features, chronological 80/20 split, Naive/Ridge/Random Forest comparison, residual thresholding and Isolation Forest.

## Project structure
```text
air_quality_fullstack/
├── index.html
├── styles.css
├── script.js
├── README.md
└── backend/
    ├── main.py
    └── requirements.txt
```

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder and create/activate a virtual environment if desired.
3. Install backend dependencies:
   `pip install -r backend/requirements.txt`
4. Start the API from the project root:
   `uvicorn backend.main:app --reload`
5. Serve the frontend from the project root in another terminal:
   `python -m http.server 5500`
6. Open `http://localhost:5500` and upload your AirQualityUCI Excel file.

The frontend calls the API at `http://127.0.0.1:8000`. For hosted deployment, change `API_URL` in `script.js` to your deployed backend URL.

## Public deployment
This is a frontend + backend application, so both parts must be hosted:
- Frontend: GitHub Pages, Netlify, or Vercel (publish `index.html`, `styles.css`, and `script.js`).
- Backend: Render, Railway, or another Python ASGI host. Set its start command to `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- Update `API_URL` in `script.js` to the deployed backend's HTTPS URL and redeploy the frontend.
- Configure backend CORS to allow only your deployed frontend origin before production use; the demo currently allows all origins.

## Dataset
The notebook references `AirQualityUCI.xlsx`, but the dataset was not included with the uploaded notebook. Upload the Excel file through the web interface when using the app. Expected columns are Date, Time, CO(GT), PT08.S1(CO), PT08.S2(NMHC), PT08.S3(NOx), PT08.S4(NO2), PT08.S5(O3), T, RH, AH.

## Notes
- This is an analysis demo, not a live sensor feed or regulatory warning service.
- The browser uses Chart.js from a CDN, so charts require internet access.
- For a production deployment, add authentication, upload limits, stricter CORS, and privacy/security controls.
