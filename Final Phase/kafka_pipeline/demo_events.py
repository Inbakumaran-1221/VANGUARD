from producer import AccessibilityEventProducer


def run_demo_events() -> None:
    producer = AccessibilityEventProducer()

    producer.send_complaint("STN-10", "No ramp at bus stop and wheelchair access blocked")
    producer.send_complaint("CEN-01", "Audio announcement missing at platform")
    producer.send_complaint("OLD-05", "Tactile paving broken and elevator not working")

    producer.send_image_signal("STN-10", ["ramp_missing", "tactile_missing"])
    producer.send_image_signal("CEN-01", ["audio_broken", "signage_unclear"])

    producer.send_transport_update("OLD-05", {"hasRamp": True, "hasAudio": True})

    producer.close()
    print("Demo Kafka events published.")


if __name__ == "__main__":
    run_demo_events()
