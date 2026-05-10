import numpy as np
import joblib
import os
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

MODEL_PATH = "ids_model.joblib"
FEATURES = ["packet_count", "byte_count", "duration", "protocol",
            "destination_port", "connections_per_second"]


def generate_training_data(n_normal: int = 5000, n_anomaly: int = 500) -> np.ndarray:
    rng = np.random.default_rng(42)

    normal = np.column_stack([
        rng.integers(1, 200, n_normal),          # packet_count
        rng.integers(100, 100_000, n_normal),     # byte_count
        rng.uniform(0.1, 60.0, n_normal),         # duration
        rng.choice([6, 17, 1], n_normal),         # protocol (TCP/UDP/ICMP)
        rng.choice([80, 443, 53, 22, 8080, 3306, 5432], n_normal),  # dest_port
        rng.uniform(0.01, 5.0, n_normal),         # connections_per_second
    ])

    port_scan = np.column_stack([
        rng.integers(1, 10, n_anomaly // 3),
        rng.integers(40, 400, n_anomaly // 3),
        rng.uniform(0.001, 0.5, n_anomaly // 3),
        rng.choice([6], n_anomaly // 3),
        rng.integers(1, 65535, n_anomaly // 3),
        rng.uniform(80.0, 500.0, n_anomaly // 3),
    ])

    dos = np.column_stack([
        rng.integers(5000, 50000, n_anomaly // 3),
        rng.integers(5_000_000, 50_000_000, n_anomaly // 3),
        rng.uniform(0.001, 1.0, n_anomaly // 3),
        rng.choice([6, 17], n_anomaly // 3),
        rng.choice([80, 443], n_anomaly // 3),
        rng.uniform(500.0, 5000.0, n_anomaly // 3),
    ])

    brute = np.column_stack([
        rng.integers(50, 500, n_anomaly // 3),
        rng.integers(10_000, 500_000, n_anomaly // 3),
        rng.uniform(30.0, 600.0, n_anomaly // 3),
        rng.choice([6], n_anomaly // 3),
        rng.choice([22, 3389, 21, 23], n_anomaly // 3),
        rng.uniform(1.0, 10.0, n_anomaly // 3),
    ])

    return np.vstack([normal, port_scan, dos, brute])


def train_model() -> Pipeline:
    print("Generating training data...")
    X_train = generate_training_data()

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            n_estimators=200,
            max_samples="auto",
            contamination=0.08,
            random_state=42,
            n_jobs=-1
        ))
    ])

    print(f"Training Isolation Forest on {len(X_train)} samples...")
    pipeline.fit(X_train)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return pipeline


def load_or_train() -> Pipeline:
    if os.path.exists(MODEL_PATH):
        print(f"Loading model from {MODEL_PATH}")
        return joblib.load(MODEL_PATH)
    return train_model()


def predict(pipeline: Pipeline, features: list) -> dict:
    X = np.array(features, dtype=float).reshape(1, -1)
    raw_score = pipeline.decision_function(X)[0]
    label = pipeline.predict(X)[0]
    is_anomaly = label == -1

    # Normalize score to [0, 1] where 1 = most anomalous
    # decision_function returns negative scores for anomalies
    anomaly_score = float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0))
    confidence = min(abs(raw_score) * 2, 1.0)

    return {
        "anomaly": is_anomaly,
        "anomalyScore": round(anomaly_score, 4),
        "confidence": round(float(confidence), 4),
        "label": "ANOMALY" if is_anomaly else "NORMAL"
    }
