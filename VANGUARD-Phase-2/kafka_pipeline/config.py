import os
from pathlib import Path

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "accessibility-auditor-consumer")
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = Path(os.getenv("STATE_PATH", BASE_DIR / "output" / "state.json"))
