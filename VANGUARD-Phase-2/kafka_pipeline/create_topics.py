from kafka.admin import KafkaAdminClient, NewTopic

from config import KAFKA_BOOTSTRAP_SERVERS
from topics import ALL_TOPICS


def create_topics() -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, client_id="access-audit-topic-admin")

    existing_topics = set(admin.list_topics())
    new_topics = []
    for topic in ALL_TOPICS:
        if topic not in existing_topics:
            new_topics.append(NewTopic(name=topic, num_partitions=1, replication_factor=1))

    if new_topics:
        admin.create_topics(new_topics=new_topics, validate_only=False)
        print(f"Created topics: {[t.name for t in new_topics]}")
    else:
        print("All topics already exist.")

    admin.close()


if __name__ == "__main__":
    create_topics()
