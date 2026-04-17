import json
from datetime import datetime, timezone

from kafka import KafkaConsumer

from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_GROUP_ID, STATE_PATH
from topics import ALL_TOPICS, COMPLAINTS_TOPIC, IMAGES_TOPIC, TRANSPORT_TOPIC


def base_stop_state() -> dict:
    return {
        "score": 100,
        "priority": "low",
        "complaints": 0,
        "tags": {},
        "last_update": None,
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))

    return {
        "stops": {},
        "theme_totals": {},
        "last_updated": None,
    }


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ensure_stop(state: dict, stop_id: str) -> dict:
    if stop_id not in state["stops"]:
        state["stops"][stop_id] = base_stop_state()
    return state["stops"][stop_id]


def get_priority(score: int) -> str:
    if score < 35:
        return "critical"
    if score < 55:
        return "high"
    if score < 75:
        return "medium"
    return "low"


def apply_penalty(stop_state: dict, points: int) -> None:
    stop_state["score"] = max(0, stop_state["score"] - points)
    stop_state["priority"] = get_priority(stop_state["score"])
    stop_state["last_update"] = datetime.now(timezone.utc).isoformat()


def process_complaint(state: dict, event: dict) -> None:
    stop_id = event.get("stop_id", "UNKNOWN")
    complaint = str(event.get("complaint", "")).lower()

    stop_state = ensure_stop(state, stop_id)
    stop_state["complaints"] += 1

    keyword_penalties = {
        "ramp": 16,
        "wheelchair": 16,
        "audio": 12,
        "announcement": 12,
        "tactile": 12,
        "elevator": 10,
        "signage": 8,
    }

    applied = False
    for keyword, penalty in keyword_penalties.items():
        if keyword in complaint:
            stop_state["tags"][keyword] = stop_state["tags"].get(keyword, 0) + 1
            state["theme_totals"][keyword] = state["theme_totals"].get(keyword, 0) + 1
            apply_penalty(stop_state, penalty)
            applied = True

    if not applied:
        apply_penalty(stop_state, 6)


def process_image_signal(state: dict, event: dict) -> None:
    stop_id = event.get("stop_id", "UNKNOWN")
    tags = event.get("tags", [])

    stop_state = ensure_stop(state, stop_id)
    for tag in tags:
        normalized = str(tag).lower()
        stop_state["tags"][normalized] = stop_state["tags"].get(normalized, 0) + 1
        state["theme_totals"][normalized] = state["theme_totals"].get(normalized, 0) + 1

        if "missing" in normalized or "broken" in normalized:
            apply_penalty(stop_state, 10)


def process_transport_update(state: dict, event: dict) -> None:
    stop_id = event.get("stop_id", "UNKNOWN")
    updates = event.get("updates", {})

    stop_state = ensure_stop(state, stop_id)

    # Positive infrastructure updates recover score gradually.
    if updates.get("hasRamp") is True:
        stop_state["score"] = min(100, stop_state["score"] + 10)
    if updates.get("hasTactile") is True:
        stop_state["score"] = min(100, stop_state["score"] + 8)
    if updates.get("hasAudio") is True:
        stop_state["score"] = min(100, stop_state["score"] + 8)

    stop_state["priority"] = get_priority(stop_state["score"])
    stop_state["last_update"] = datetime.now(timezone.utc).isoformat()


def process_event(state: dict, topic: str, event: dict) -> None:
    if topic == COMPLAINTS_TOPIC:
        process_complaint(state, event)
    elif topic == IMAGES_TOPIC:
        process_image_signal(state, event)
    elif topic == TRANSPORT_TOPIC:
        process_transport_update(state, event)


def run() -> None:
    consumer = KafkaConsumer(
        *ALL_TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
        enable_auto_commit=True,
    )

    state = load_state()
    print("Kafka consumer started. Waiting for events...")

    for message in consumer:
        event = message.value
        process_event(state, message.topic, event)
        save_state(state)

        stop_id = event.get("stop_id", "UNKNOWN")
        score = state["stops"][stop_id]["score"]
        priority = state["stops"][stop_id]["priority"]
        print(f"[{message.topic}] stop={stop_id} score={score} priority={priority}")


if __name__ == "__main__":
    run()
