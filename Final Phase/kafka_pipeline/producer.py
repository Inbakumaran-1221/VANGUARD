import json
from datetime import datetime, timezone

from kafka import KafkaProducer

from config import KAFKA_BOOTSTRAP_SERVERS
from topics import COMPLAINTS_TOPIC, IMAGES_TOPIC, TRANSPORT_TOPIC


class AccessibilityEventProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8") if key else None,
        )

    def send(self, topic: str, payload: dict, key: str | None = None) -> None:
        event = {
            "event_time": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self.producer.send(topic, key=key, value=event)

    def send_complaint(self, stop_id: str, complaint: str, source: str = "portal") -> None:
        self.send(
            COMPLAINTS_TOPIC,
            {
                "event_type": "complaint",
                "stop_id": stop_id,
                "complaint": complaint,
                "source": source,
            },
            key=stop_id,
        )

    def send_image_signal(self, stop_id: str, tags: list[str], image_url: str = "") -> None:
        self.send(
            IMAGES_TOPIC,
            {
                "event_type": "image_signal",
                "stop_id": stop_id,
                "tags": tags,
                "image_url": image_url,
            },
            key=stop_id,
        )

    def send_transport_update(self, stop_id: str, updates: dict) -> None:
        self.send(
            TRANSPORT_TOPIC,
            {
                "event_type": "transport_update",
                "stop_id": stop_id,
                "updates": updates,
            },
            key=stop_id,
        )

    def close(self) -> None:
        self.producer.flush()
        self.producer.close()


if __name__ == "__main__":
    producer = AccessibilityEventProducer()
    producer.send_complaint("STN-10", "No ramp at the east gate")
    producer.send_image_signal("CEN-01", ["ramp_missing", "tactile_missing"])
    producer.send_transport_update("UNI-03", {"hasAudio": False, "audited": True})
    producer.close()
    print("Sample events sent.")
