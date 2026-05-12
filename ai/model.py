"""
Anomaly detection model — trained on CICIDS2017 or synthetic fallback.

Feature set (12 features aligned with CICFlowMeter output):
  destination_port, protocol, flow_duration, total_fwd_packets,
  total_bwd_packets, total_fwd_bytes, total_bwd_bytes,
  flow_bytes_per_sec, flow_packets_per_sec,
  syn_flag_count, rst_flag_count, avg_packet_size
"""

import os
import glob
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

MODEL_PATH = "ids_model.joblib"
DATA_DIR = "data"

FEATURES = [
    "destination_port",
    "protocol",
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_fwd_bytes",
    "total_bwd_bytes",
    "flow_bytes_per_sec",
    "flow_packets_per_sec",
    "syn_flag_count",
    "rst_flag_count",
    "avg_packet_size",
]

# Mapping from CICIDS2017 column names (after strip) to our feature names
CICIDS_COL_MAP = {
    "Destination Port":             "destination_port",
    "Protocol":                     "protocol",
    "Flow Duration":                "flow_duration",
    "Total Fwd Packets":            "total_fwd_packets",
    "Total Backward Packets":       "total_bwd_packets",
    "Total Length of Fwd Packets":  "total_fwd_bytes",
    "Total Length of Bwd Packets":  "total_bwd_bytes",
    "Flow Bytes/s":                 "flow_bytes_per_sec",
    "Flow Packets/s":               "flow_packets_per_sec",
    "SYN Flag Count":               "syn_flag_count",
    "RST Flag Count":               "rst_flag_count",
    "Average Packet Size":          "avg_packet_size",
    "Label":                        "label",
}


def load_cicids2017(data_dir: str) -> pd.DataFrame | None:
    csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    csv_files += glob.glob(os.path.join(data_dir, "*.csv"))
    csv_files = list(set(csv_files))

    if not csv_files:
        return None

    print(f"Found {len(csv_files)} CICIDS2017 file(s): {[os.path.basename(f) for f in csv_files]}")
    dfs = []
    for path in csv_files:
        try:
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip()
            dfs.append(df)
            print(f"  Loaded {os.path.basename(path)}: {len(df):,} rows")
        except Exception as e:
            print(f"  [WARN] Could not read {path}: {e}")

    if not dfs:
        return None

    combined = pd.concat(dfs, ignore_index=True)
    print(f"Total rows before cleaning: {len(combined):,}")
    return combined


def preprocess_cicids(df: pd.DataFrame) -> np.ndarray:
    # Keep only columns we need
    needed = list(CICIDS_COL_MAP.keys())
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing CICIDS2017 columns: {missing}. "
                         f"Available: {list(df.columns[:20])}")

    df = df[needed].copy()
    df.rename(columns=CICIDS_COL_MAP, inplace=True)

    # Normalise label
    df["label"] = df["label"].astype(str).str.strip()

    # Flow Duration in CICIDS2017 is in microseconds → convert to seconds
    df["flow_duration"] = df["flow_duration"] / 1_000_000.0

    # Replace inf / -inf with NaN, then drop
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(df)
    df.dropna(subset=FEATURES, inplace=True)
    after = len(df)
    if before != after:
        print(f"  Dropped {before - after:,} rows with NaN/Inf values")

    # Drop nonsensical flows (zero or negative duration)
    df = df[df["flow_duration"] > 0]

    # Cap extreme values at 99.9th percentile to reduce outlier influence on scaler
    for col in ["flow_bytes_per_sec", "flow_packets_per_sec",
                "total_fwd_packets", "total_bwd_packets",
                "total_fwd_bytes", "total_bwd_bytes"]:
        cap = df[col].quantile(0.999)
        df[col] = df[col].clip(upper=cap)

    # Keep only BENIGN for training — IDS learns "normal" behaviour
    benign = df[df["label"] == "BENIGN"]
    n_benign = len(benign)
    n_attack = len(df) - n_benign
    print(f"  BENIGN rows (training): {n_benign:,} | Attack rows (excluded from fit): {n_attack:,}")

    if n_benign < 500:
        raise ValueError(f"Too few BENIGN samples ({n_benign}). "
                         "Add more CICIDS2017 CSV files to the data/ folder.")

    X = benign[FEATURES].values.astype(np.float64)
    return X


def generate_synthetic_data(n_normal: int = 8000, n_anomaly: int = 500) -> np.ndarray:
    """Fallback when no CICIDS2017 files are present."""
    print("No CICIDS2017 data found — generating synthetic training data.")
    rng = np.random.default_rng(42)

    def normal_block(n):
        return np.column_stack([
            rng.choice([80, 443, 53, 22, 8080, 3306, 5432], n),  # destination_port
            rng.choice([6, 17, 1], n),                             # protocol
            rng.uniform(0.1, 60.0, n),                             # flow_duration
            rng.integers(1, 120, n),                               # total_fwd_packets
            rng.integers(1, 120, n),                               # total_bwd_packets
            rng.integers(100, 60_000, n),                          # total_fwd_bytes
            rng.integers(100, 60_000, n),                          # total_bwd_bytes
            rng.uniform(100, 60_000, n),                           # flow_bytes_per_sec
            rng.uniform(0.1, 10.0, n),                             # flow_packets_per_sec
            rng.integers(0, 2, n),                                 # syn_flag_count
            rng.integers(0, 1, n),                                 # rst_flag_count
            rng.uniform(100, 1000, n),                             # avg_packet_size
        ])

    k = n_anomaly // 3

    port_scan = np.column_stack([
        rng.integers(1, 65535, k),
        np.full(k, 6),
        rng.uniform(0.001, 0.1, k),
        rng.integers(1, 3, k),
        rng.integers(0, 1, k),
        rng.integers(40, 200, k),
        rng.integers(0, 100, k),
        rng.uniform(1_000, 100_000, k),
        rng.uniform(100, 1_500, k),
        rng.integers(1, 4, k),
        rng.integers(0, 3, k),
        rng.uniform(40, 100, k),
    ])

    dos = np.column_stack([
        rng.choice([80, 443], k),
        rng.choice([6, 17], k),
        rng.uniform(0.001, 2.0, k),
        rng.integers(1_000, 50_000, k),
        rng.integers(0, 100, k),
        rng.integers(1_000_000, 50_000_000, k),
        rng.integers(0, 10_000, k),
        rng.uniform(500_000, 5_000_000, k),
        rng.uniform(1_000, 10_000, k),
        rng.integers(0, 5, k),
        rng.integers(0, 5, k),
        rng.uniform(50, 150, k),
    ])

    brute = np.column_stack([
        rng.choice([22, 3389, 21, 23], k),
        np.full(k, 6),
        rng.uniform(10, 600, k),
        rng.integers(50, 500, k),
        rng.integers(50, 500, k),
        rng.integers(5_000, 200_000, k),
        rng.integers(5_000, 200_000, k),
        rng.uniform(100, 2_000, k),
        rng.uniform(0.5, 5.0, k),
        rng.integers(1, 5, k),
        rng.integers(0, 3, k),
        rng.uniform(100, 500, k),
    ])

    return np.vstack([normal_block(n_normal), port_scan, dos, brute])


def train_model(data_dir: str = DATA_DIR) -> Pipeline:
    df = load_cicids2017(data_dir)

    if df is not None:
        print("Preprocessing CICIDS2017 dataset...")
        X_train = preprocess_cicids(df)
        # Training on BENIGN only → very low expected contamination during inference
        contamination = 0.01
    else:
        X_train = generate_synthetic_data()
        contamination = 0.08

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            n_estimators=200,
            max_samples=min(len(X_train), 256),
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        ))
    ])

    print(f"Training Isolation Forest on {len(X_train):,} samples "
          f"({len(FEATURES)} features, contamination={contamination})...")
    pipeline.fit(X_train)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved → {MODEL_PATH}")
    return pipeline


def load_or_train(data_dir: str = DATA_DIR) -> Pipeline:
    if os.path.exists(MODEL_PATH):
        print(f"Loading saved model from {MODEL_PATH}")
        return joblib.load(MODEL_PATH)
    return train_model(data_dir)


def predict(pipeline: Pipeline, features: list) -> dict:
    X = np.array(features, dtype=np.float64).reshape(1, -1)
    # Replace any inf that might slip through from sensor
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=0.0)

    raw_score = pipeline.decision_function(X)[0]
    label = pipeline.predict(X)[0]
    is_anomaly = label == -1

    # decision_function: positive = normal, negative = anomaly
    # Remap to [0, 1] where 1 = most anomalous
    anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
    confidence = float(np.clip(abs(raw_score) * 2, 0.0, 1.0))

    return {
        "anomaly": is_anomaly,
        "anomalyScore": round(anomaly_score, 4),
        "confidence": round(confidence, 4),
        "label": "ANOMALY" if is_anomaly else "NORMAL",
    }
