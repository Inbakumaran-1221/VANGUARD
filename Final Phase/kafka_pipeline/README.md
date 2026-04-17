# Kafka Pipeline (Separate Service)

This folder contains a separate real-time streaming service for the AccessAudit project.

## What this service does

- Ingests live events from Kafka topics:
  - `complaints_topic`
  - `images_topic`
  - `transport_topic`
- Processes events continuously using a consumer.
- Updates per-stop accessibility score and priority in:
  - `kafka_pipeline/output/state.json`

## Files

- `producer.py`: sends complaint/image/transport events.
- `consumer.py`: listens to all topics and updates state.
- `create_topics.py`: creates required Kafka topics.
- `demo_events.py`: publishes sample events to test the flow.
- `config.py`: environment config.
- `topics.py`: topic constants.

## Local setup

1. Start Kafka broker:

```bash
docker compose -f docker-compose.kafka.yml up -d
```

2. Install Python dependencies:

```powershell
cd kafka_pipeline
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. Create topics:

```bash
python create_topics.py
```

4. Start consumer (terminal 1):

```bash
python consumer.py
```

5. Publish demo events (terminal 2):

```bash
python demo_events.py
```

## Result

As events arrive, `output/state.json` is updated with:

- Per-stop score and priority
- Complaint/theme counters
- Global theme totals
- Last update time

## Integration direction

Your frontend can poll `output/state.json` through a simple API layer (FastAPI/Flask/Node) to show near real-time score/map updates.
