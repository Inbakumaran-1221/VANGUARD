import os
import socket
from csv import DictWriter
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from pymongo import ReturnDocument

try:
    import cv2
    import numpy as np
    from ultralytics import YOLO
except Exception:
    cv2 = None
    np = None
    YOLO = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "yolov8n.pt"
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(DEFAULT_MODEL if DEFAULT_MODEL.exists() else "yolov8n.pt"))
CONF_THRESHOLD = float(os.getenv("YOLO_CONFIDENCE", "0.25"))
MIN_FEATURE_CONF = float(os.getenv("FEATURE_CONFIDENCE", "0.30"))
DEFAULT_PORT = int(os.getenv("PORT", "5001"))
MAX_PORT_SCAN = int(os.getenv("PORT_SCAN_LIMIT", "20"))
DEBUG_DETECTIONS = os.getenv("DEBUG_DETECTIONS", "0") == "1"
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "accessaudit")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "feedback")
MONGODB_STATE_COLLECTION_NAME = os.getenv("MONGODB_STATE_COLLECTION_NAME", "shared_state")
MONGODB_STATE_DOC_ID = os.getenv("MONGODB_STATE_DOC_ID", "shared-state")
MONGODB_TIMEOUT_MS = int(os.getenv("MONGODB_TIMEOUT_MS", "5000"))

app = Flask(__name__)
CORS(app)
model = YOLO(MODEL_PATH) if YOLO is not None else None
_mongo_client: MongoClient | None = None
_feedback_collection: Collection[Any] | None = None
_state_collection: Collection[Any] | None = None
_feedback_connection_error: str | None = None
_state_connection_error: str | None = None

FEATURE_CLASS_MAP = {
    "ramp": {"ramp", "wheelchair", "access ramp"},
    "stairs": {"stairs", "staircase", "steps"},
    "tactile": {"tactile", "tactile paving", "warning tile"},
    "braille": {"braille", "braille sign", "braille board"},
}

FEATURE_KEYS = ("ramp", "stairs", "tactile", "braille")

CITY_BY_PREFIX = {
    "DEL": "Delhi",
    "MUM": "Mumbai",
    "BLR": "Bengaluru",
    "CHE": "Chennai",
    "KOL": "Kolkata",
    "HYD": "Hyderabad",
    "PUN": "Pune",
    "AHM": "Ahmedabad",
    "JAI": "Jaipur",
    "LKO": "Lucknow",
    "KOC": "Kochi",
    "BHO": "Bhopal",
    "PAT": "Patna",
    "BBS": "Bhubaneswar",
    "CHD": "Chandigarh",
    "GHY": "Guwahati",
}


def _normalize_label(raw_label: str) -> str:
    return raw_label.strip().lower().replace("_", " ").replace("-", " ")


def _class_to_feature(label: str) -> str | None:
    normalized = _normalize_label(label)

    if any(keyword in normalized for keyword in ("ramp", "wheelchair", "accessible")):
        return "ramp"
    if any(keyword in normalized for keyword in ("stairs", "staircase", "steps", "step")):
        return "stairs"
    if any(keyword in normalized for keyword in ("tactile", "paving", "warning tile", "guiding block")):
        return "tactile"
    if "braille" in normalized:
        return "braille"

    return None


def _safe_image_from_upload(raw_bytes: bytes) -> Any:
    if cv2 is None or np is None:
        raise RuntimeError("Image analysis dependencies are not installed")

    if not raw_bytes:
        raise ValueError("Uploaded file is empty")

    image_array = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode uploaded image")
    return image


def _extract_detections(prediction: Any) -> list[dict[str, Any]]:
    boxes = prediction.boxes
    if boxes is None or boxes.data is None:
        return []

    detections: list[dict[str, Any]] = []
    class_names = prediction.names

    for row in boxes.data.tolist():
        x1, y1, x2, y2, confidence, class_id = row
        label = class_names.get(int(class_id), str(int(class_id)))
        detections.append(
            {
                "class": label,
                "confidence": round(float(confidence), 4),
                "bbox": {
                    "x1": round(float(x1), 2),
                    "y1": round(float(y1), 2),
                    "x2": round(float(x2), 2),
                    "y2": round(float(y2), 2),
                },
            }
        )

    return detections


def _derive_features(detections: list[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    # Unknown means "not enough evidence" (avoids false negatives from generic COCO classes).
    features: dict[str, Any] = {key: None for key in FEATURE_KEYS}
    matched_any_accessibility_class = False

    for detection in detections:
        if float(detection["confidence"]) < MIN_FEATURE_CONF:
            continue

        label = detection["class"]
        normalized = _normalize_label(label)

        for feature_name, aliases in FEATURE_CLASS_MAP.items():
            if normalized in aliases:
                features[feature_name] = True
                matched_any_accessibility_class = True

        mapped = _class_to_feature(normalized)
        if mapped is not None:
            features[mapped] = True
            matched_any_accessibility_class = True

    if matched_any_accessibility_class:
        for feature_name in FEATURE_KEYS:
            if features[feature_name] is None:
                features[feature_name] = False

    return features, matched_any_accessibility_class


def _derive_gap_messages(features: dict[str, Any], has_accessibility_match: bool) -> list[str]:
    gap_messages: list[str] = []

    if not has_accessibility_match:
        gap_messages.append("No accessibility-specific detections from base model")
        gap_messages.append("Result is inconclusive. Upload clearer evidence or use a custom-trained model")
        return gap_messages

    if features["ramp"] is False:
        gap_messages.append("Ramp missing")
    if features["stairs"] is True and features["ramp"] is False:
        gap_messages.append("Stairs detected without accessible ramp")
    if features["tactile"] is False:
        gap_messages.append("Tactile path not detected")
    if features["braille"] is False:
        gap_messages.append("Braille signage not detected")

    return gap_messages


def _find_open_port(start_port: int, scan_limit: int) -> int:
    for port in range(start_port, start_port + scan_limit + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + scan_limit}")


def _get_mongo_client() -> MongoClient:
    global _mongo_client, _feedback_connection_error, _state_connection_error

    if _mongo_client is not None:
        return _mongo_client

    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS)
        client.admin.command("ping")
        _mongo_client = client
        _feedback_connection_error = None
        _state_connection_error = None
        return client
    except PyMongoError as exc:
        error_message = f"MongoDB unavailable at {MONGODB_URI}: {exc}"
        _feedback_connection_error = error_message
        _state_connection_error = error_message
        raise RuntimeError(error_message) from exc


def _get_feedback_collection() -> Collection[Any]:
    global _feedback_collection

    if _feedback_collection is not None:
        return _feedback_collection

    try:
        client = _get_mongo_client()
        collection = client[MONGODB_DB_NAME][MONGODB_COLLECTION_NAME]
        collection.create_index([("createdAt", -1)])
        collection.create_index([("city", 1), ("severity", 1), ("createdAt", -1)])
        _feedback_collection = collection
        return collection
    except PyMongoError as exc:
        _feedback_connection_error = f"MongoDB unavailable at {MONGODB_URI}: {exc}"
        raise RuntimeError(_feedback_connection_error) from exc


def _feedback_connection_ready() -> bool:
    return _feedback_collection is not None and _feedback_connection_error is None


def _get_state_collection() -> Collection[Any]:
    global _state_collection, _state_connection_error

    if _state_collection is not None:
        return _state_collection

    try:
        client = _get_mongo_client()
        collection = client[MONGODB_DB_NAME][MONGODB_STATE_COLLECTION_NAME]
        collection.create_index([("updatedAt", -1)])
        _state_collection = collection
        return collection
    except PyMongoError as exc:
        _state_connection_error = f"MongoDB unavailable at {MONGODB_URI}: {exc}"
        raise RuntimeError(_state_connection_error) from exc


def _state_connection_ready() -> bool:
    return _state_collection is not None and _state_connection_error is None


def _coerce_created_at(raw_value: Any) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value if raw_value.tzinfo is not None else raw_value.replace(tzinfo=timezone.utc)

    if isinstance(raw_value, str):
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return datetime.now(timezone.utc)


def _serialize_feedback(document: dict[str, Any]) -> dict[str, Any]:
    created_at = document.get("createdAt")
    if isinstance(created_at, datetime):
        created_at_value = created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        created_at_value = str(created_at) if created_at is not None else ""

    identifier = str(document.get("_id", ""))
    return {
        "dbId": identifier,
        "id": identifier,
        "stopId": document.get("stopId", "UNASSIGNED"),
        "city": document.get("city", "Unknown"),
        "severity": document.get("severity", "medium"),
        "message": document.get("message", ""),
        "createdAt": created_at_value,
    }


def _city_from_stop_id(stop_id: str) -> str:
    prefix = stop_id.split("-", 1)[0].upper()
    return CITY_BY_PREFIX.get(prefix, "Unknown")


def _parse_feedback_object_id(raw_id: str) -> ObjectId | None:
    try:
        return ObjectId(raw_id.strip())
    except (InvalidId, AttributeError):
        return None


def _build_feedback_query(city: str | None, severity: str | None) -> dict[str, Any]:
    query: dict[str, Any] = {}

    if city:
        query["city"] = city

    if severity:
        query["severity"] = severity

    return query


def _sync_state_user_feedback(feedback_items: list[dict[str, Any]]) -> None:
    collection = _get_state_collection()
    document = collection.find_one({"_id": MONGODB_STATE_DOC_ID}) or {}
    collection.replace_one(
        {"_id": MONGODB_STATE_DOC_ID},
        {
            "_id": MONGODB_STATE_DOC_ID,
            "stops": document.get("stops", []),
            "grievancesText": document.get("grievancesText", ""),
            "userFeedback": feedback_items,
            "updatedAt": datetime.now(timezone.utc),
        },
        upsert=True,
    )


def _serialize_state_document(document: dict[str, Any]) -> dict[str, Any]:
    updated_at = document.get("updatedAt")
    if isinstance(updated_at, datetime):
        updated_at_value = updated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        updated_at_value = str(updated_at) if updated_at is not None else ""

    return {
        "stops": document.get("stops", []),
        "grievancesText": document.get("grievancesText", ""),
        "userFeedback": document.get("userFeedback", []),
        "updatedAt": updated_at_value,
    }


def _normalize_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    stops = payload.get("stops")
    grievances_text = payload.get("grievancesText")
    user_feedback = payload.get("userFeedback")

    if not isinstance(stops, list):
        raise ValueError("State payload must include a stops array.")
    if not isinstance(grievances_text, str):
        raise ValueError("State payload must include grievancesText as a string.")
    if not isinstance(user_feedback, list):
        raise ValueError("State payload must include userFeedback as an array.")

    return {
        "stops": stops,
        "grievancesText": grievances_text,
        "userFeedback": user_feedback,
        "updatedAt": datetime.now(timezone.utc),
    }


@app.get("/health")
def health() -> tuple[dict[str, Any], int]:
    return {
        "status": "ok",
        "model": MODEL_PATH,
        "confidenceThreshold": CONF_THRESHOLD,
        "feedbackStore": "mongodb",
        "feedbackStoreReady": _feedback_connection_ready(),
        "stateStore": "mongodb",
        "stateStoreReady": _state_connection_ready(),
        "imageAnalysisEnabled": model is not None,
    }, 200


@app.get("/state")
def get_state() -> tuple[dict[str, Any], int]:
    try:
        collection = _get_state_collection()
        document = collection.find_one({"_id": MONGODB_STATE_DOC_ID})
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    if document is None:
        return {"error": "State not found."}, 404

    return {"state": _serialize_state_document(document)}, 200


@app.put("/state")
def save_state() -> tuple[dict[str, Any], int]:
    payload = request.get_json(silent=True) or {}

    try:
        state_document = _normalize_state_payload(payload)
    except ValueError as exc:
        return {"error": str(exc)}, 400

    try:
        collection = _get_state_collection()
        collection.replace_one(
            {"_id": MONGODB_STATE_DOC_ID},
            {"_id": MONGODB_STATE_DOC_ID, **state_document},
            upsert=True,
        )
        stored = collection.find_one({"_id": MONGODB_STATE_DOC_ID})
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    if stored is None:
        return {"error": "Failed to store state."}, 500

    return {"state": _serialize_state_document(stored)}, 200


@app.post("/analyze")
def analyze() -> tuple[dict[str, Any], int]:
    if model is None:
        return {
            "error": "Image analysis dependencies are not installed in this environment.",
            "hint": "Install the optional ML dependencies if you want /analyze to run.",
        }, 503

    print("Request received")
    file_from_form = request.files.get("file")
    image_from_form = request.files.get("image")
    print("File:", file_from_form)
    print("Image:", image_from_form)

    uploaded_file = file_from_form or image_from_form
    if uploaded_file is None:
        return {"error": "Missing image file. Use form-data key 'image' or 'file'."}, 400

    try:
        image = _safe_image_from_upload(uploaded_file.read())
    except ValueError as exc:
        return {"error": str(exc)}, 400

    requested_conf = request.form.get("confidence")
    confidence_used = CONF_THRESHOLD
    if requested_conf is not None:
        try:
            parsed_conf = float(requested_conf)
            confidence_used = min(max(parsed_conf, 0.05), 0.95)
        except ValueError:
            return {"error": "Invalid confidence value. Use a number between 0.05 and 0.95."}, 400

    prediction = model(image, conf=confidence_used)[0]
    detections = _extract_detections(prediction)
    print("Detections:", detections)

    raw_response = request.args.get("raw") == "1" or request.form.get("raw") == "1"
    if raw_response:
        return jsonify({"detections": detections, "count": len(detections)}), 200

    if DEBUG_DETECTIONS:
        print("[analyze] detections=", detections)

    features, has_accessibility_match = _derive_features(detections)
    gap_messages = _derive_gap_messages(features, has_accessibility_match)

    if DEBUG_DETECTIONS:
        print("[analyze] features=", features, "inconclusive=", not has_accessibility_match)

    response = {
        "detections": detections,
        "features": features,
        "gaps": gap_messages,
        "inconclusive": not has_accessibility_match,
        "summary": {
            "detectedObjects": len(detections),
            "model": Path(MODEL_PATH).name,
            "confidenceUsed": confidence_used,
            "featureConfidence": MIN_FEATURE_CONF,
        },
        "note": "Default YOLO weights are generic. For reliable ramp/tactile/braille detection, train a custom model and map those classes.",
    }
    return jsonify(response), 200


@app.get("/feedback")
def list_feedback() -> tuple[dict[str, Any], int]:
    raw_limit = request.args.get("limit", "50")
    try:
        limit = max(1, min(int(raw_limit), 200))
    except ValueError:
        return {"error": "Invalid limit. Use an integer between 1 and 200."}, 400

    city = request.args.get("city")
    severity = request.args.get("severity")
    try:
        collection = _get_feedback_collection()
        rows = list(collection.find(_build_feedback_query(city, severity)).sort("createdAt", -1).limit(limit))
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    items = [_serialize_feedback(row) for row in rows]
    return {"items": items, "count": len(items)}, 200


@app.post("/feedback")
def create_feedback() -> tuple[dict[str, Any], int]:
    payload = request.get_json(silent=True) or {}

    stop_id = str(payload.get("stopId") or "UNASSIGNED").strip() or "UNASSIGNED"
    city = str(payload.get("city") or _city_from_stop_id(stop_id)).strip() or "Unknown"
    severity = str(payload.get("severity") or "medium").strip().lower()
    message = str(payload.get("message") or "").strip()

    if not message:
        return {"error": "Message is required."}, 400

    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"

    try:
        collection = _get_feedback_collection()
        document = {
            "stopId": stop_id,
            "city": city,
            "severity": severity,
            "message": message,
            "createdAt": _coerce_created_at(payload.get("createdAt")),
        }
        inserted = collection.insert_one(document)
        row = collection.find_one({"_id": inserted.inserted_id})
        if row is not None:
            try:
                existing_state = _get_state_collection().find_one({"_id": MONGODB_STATE_DOC_ID}) or {}
                current_feedback = list(existing_state.get("userFeedback", []))
                current_feedback.insert(0, _serialize_feedback(row))
                _sync_state_user_feedback(current_feedback)
            except RuntimeError:
                pass
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    if row is None:
        return {"error": "Failed to store feedback."}, 500

    return {"item": _serialize_feedback(row)}, 201


@app.put("/feedback/<feedback_id>")
def update_feedback(feedback_id: str) -> tuple[dict[str, Any], int]:
    object_id = _parse_feedback_object_id(feedback_id)
    if object_id is None:
        return {"error": "Invalid feedback id."}, 400

    payload = request.get_json(silent=True) or {}
    severity = str(payload.get("severity") or "").strip().lower()
    message = str(payload.get("message") or "").strip()

    update_fields: list[str] = []
    update_args: list[str] = []

    if message:
        update_fields.append("message = ?")
        update_args.append(message)

    if severity:
        if severity not in {"low", "medium", "high", "critical"}:
            return {"error": "Invalid severity."}, 400
        update_fields.append("severity = ?")
        update_args.append(severity)

    if not update_fields:
        return {"error": "No updatable fields provided."}, 400

    try:
        collection = _get_feedback_collection()
        row = collection.find_one_and_update(
            {"_id": object_id},
            {"$set": dict(zip([field.split(" = ")[0] for field in update_fields], update_args))},
            return_document=ReturnDocument.AFTER,
        )
        if row is not None:
            try:
                existing_state = _get_state_collection().find_one({"_id": MONGODB_STATE_DOC_ID}) or {}
                current_feedback = list(existing_state.get("userFeedback", []))
                updated_feedback = []
                for item in current_feedback:
                    if item.get("id") == str(object_id):
                        updated_feedback.append(_serialize_feedback(row))
                    else:
                        updated_feedback.append(item)
                _sync_state_user_feedback(updated_feedback)
            except RuntimeError:
                pass
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    if row is None:
        return {"error": "Feedback not found."}, 404

    return {"item": _serialize_feedback(row)}, 200


@app.delete("/feedback/<feedback_id>")
def delete_feedback(feedback_id: str) -> tuple[dict[str, Any], int]:
    object_id = _parse_feedback_object_id(feedback_id)
    if object_id is None:
        return {"error": "Invalid feedback id."}, 400

    try:
        collection = _get_feedback_collection()
        result = collection.delete_one({"_id": object_id})
        if result.deleted_count > 0:
            try:
                existing_state = _get_state_collection().find_one({"_id": MONGODB_STATE_DOC_ID}) or {}
                current_feedback = list(existing_state.get("userFeedback", []))
                updated_feedback = [item for item in current_feedback if item.get("id") != str(object_id)]
                _sync_state_user_feedback(updated_feedback)
            except RuntimeError:
                pass
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    if result.deleted_count == 0:
        return {"error": "Feedback not found."}, 404

    return {"ok": True}, 200


@app.get("/feedback/export.csv")
def export_feedback_csv() -> Response:
    city = request.args.get("city")
    severity = request.args.get("severity")
    try:
        collection = _get_feedback_collection()
        rows = list(collection.find(_build_feedback_query(city, severity)).sort("createdAt", -1))
    except RuntimeError as exc:
        return Response(str(exc), status=503, mimetype="text/plain")

    output = StringIO()
    writer = DictWriter(output, fieldnames=["id", "stop_id", "city", "severity", "message", "created_at"])
    writer.writeheader()
    for row in rows:
        created_at = row.get("createdAt")
        if isinstance(created_at, datetime):
            created_at_value = created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            created_at_value = str(created_at) if created_at is not None else ""

        writer.writerow(
            {
                "id": str(row.get("_id", "")),
                "stop_id": row.get("stopId", "UNASSIGNED"),
                "city": row.get("city", "Unknown"),
                "severity": row.get("severity", "medium"),
                "message": row.get("message", ""),
                "created_at": created_at_value,
            }
        )

    csv_payload = output.getvalue()
    output.close()

    return Response(
        csv_payload,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedback-export.csv"},
    )


if __name__ == "__main__":
    selected_port = _find_open_port(DEFAULT_PORT, MAX_PORT_SCAN)
    if selected_port != DEFAULT_PORT:
        print(f"Port {DEFAULT_PORT} is busy, using {selected_port} instead.")

    app.run(
        host="0.0.0.0",
        port=selected_port,
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        use_reloader=False,
    )
