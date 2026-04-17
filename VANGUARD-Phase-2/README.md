# AccessAudit

AccessAudit is a transit accessibility review workspace for city operations, planners, and inspection teams. It combines a multi-page frontend for stop-level analysis with a separate Kafka pipeline for streaming updates and demo event processing.

## What It Does

The product helps teams identify where public transport accessibility breaks down, prioritize the highest-risk stops, and turn complaints or field evidence into a clear audit trail.

Core capabilities:

- Stop-level accessibility scoring across ramp, elevator, tactile, braille, audio, and low-floor access
- Grievance clustering by theme, including ramp, audio, tactile, and signage issues
- Priority ranking for urgent intervention and follow-up
- Evidence review with image labels, detection boxes, and confidence values
- Report views for audit summaries and export-ready output
- Separate Kafka service for streaming state updates and demo ingestion

## Repository Layout

- [index.html](index.html) and [dashboard.js](dashboard.js) for the main overview
- [transit-stops.html](transit-stops.html) and [transit-stops.js](transit-stops.js) for stop-level analysis and map views
- [grievances.html](grievances.html) and [grievances.js](grievances.js) for complaint clustering and review
- [reports.html](reports.html) and [reports.js](reports.js) for reporting and export flows
- [shared-data.js](shared-data.js) for baseline stops, scoring rules, and shared UI state
- [india-dataset.js](india-dataset.js) for India-focused transit stops and grievance demo data
- [kafka_pipeline/](kafka_pipeline/) for the separate Python streaming service

## Architecture

The frontend runs as a static Vite app. It loads shared stop data from [shared-data.js](shared-data.js) and renders each workflow on its own page instead of forcing everything into a single dashboard.

The Kafka service is intentionally separated from the frontend. It consumes complaint, image, and transport events, then writes consolidated state to [kafka_pipeline/output/state.json](kafka_pipeline/output/state.json). That keeps the browser layer simple while leaving room for a small API later if the team wants to serve live updates.

## Local Development

Requirements:

- Node.js 18 or newer
- Windows 10/11 or another supported desktop OS
- Python 3.10+ for the Kafka tooling
- MongoDB running locally at `mongodb://localhost:27017/`
- Docker Desktop if you want to run the Kafka stack locally

Start the frontend:

```bash
npm install
npm run dev
```

This now starts both the Vite frontend and the Flask YOLO backend together.

On Windows, create the backend virtual environment before starting the app if it does not already exist:

```powershell
python -m venv .venv-windows
.\.venv-windows\Scripts\activate
python -m pip install -r backend\requirements.txt
```

The backend stores feedback in MongoDB. If you want to use a different URI, set `MONGODB_URI` before running `npm run dev`.
The shared browser state used by the dashboard, transit stops, grievances, and reports pages is also synced to MongoDB through the backend `GET /state` and `PUT /state` endpoints.

Open the local Vite URL shown in the terminal, usually http://localhost:5173.

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Image Recognition Backend (Flask + YOLO)

Part 1 of the CV workflow is now implemented as a backend API in `backend/app.py`.

Install backend dependencies:

```powershell
.\.venv-windows\Scripts\activate
python -m pip install -r backend\requirements.txt
```

By default the backend connects to `mongodb://localhost:27017/` and stores feedback in the `accessaudit` database, `feedback` collection.

Run the API server:

```bash
npm run backend:dev
```

If you only want the backend, use this command. For normal development, `npm run dev` is enough.

If port `5001` is already busy, the backend will automatically use the next free port in the `5001-5021` range and the frontend will detect it.

The server starts on `http://localhost:5001` and exposes:

- `GET /health` for service/model status
- `POST /analyze` for image detection

Example request:

```bash
curl -X POST http://localhost:5001/analyze \
	-F "image=@test.jpg"
```

The response includes:

- Detected objects with class, confidence, and bounding box
- Accessibility feature flags (`ramp`, `stairs`, `tactile`, `braille`)
- Gap messages such as "Ramp missing"

Note: default YOLO weights are generic. For reliable ramp/tactile/braille detection, train a custom model and set `YOLO_MODEL_PATH` to your trained weights.

## Kafka Demo Flow

Use the Kafka stack when you want to simulate near-real-time updates.

```bash
npm run kafka:up
cd kafka_pipeline
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python create_topics.py
python consumer.py
```

In another terminal:

```bash
cd kafka_pipeline
.\.venv\Scripts\activate
python demo_events.py
```

The consumer writes the latest state to [kafka_pipeline/output/state.json](kafka_pipeline/output/state.json).

## Scoring Model

Gap score is based on the absence of accessibility features plus a complaint pressure adjustment. Missing features are weighted more heavily than the presence of a single complaint, so the model still prioritizes structural barriers over noise.

## Demo Dataset (India)

The default frontend dataset is now India-focused and includes major transit nodes across cities such as Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad, Jaipur, Lucknow, Kochi, Bhopal, Patna, Bhubaneswar, Chandigarh, and Guwahati.

The dataset source file is [india-dataset.js](india-dataset.js), and `Load Dataset` actions in the UI now use these India records through shared app state.

## Notes For Contributors

- The repo is intentionally split into separate pages to keep each workflow focused.
- Shared stop fixtures and scoring logic live in [shared-data.js](shared-data.js), so changes there affect all pages.
- The Kafka pipeline is a separate service and can be developed independently from the frontend.

## Further Reading

- [kafka_pipeline/README.md](kafka_pipeline/README.md)
