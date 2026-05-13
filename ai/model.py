"""
Anomaly detection model trained on CICIDS2017 (MachineLearningCSV variant).

Feature set — 11 features matching CICFlowMeter output, aligned with
the columns present in the CICIDS2017 MachineLearningCSV files:

  destination_port, flow_duration, total_fwd_packets, total_bwd_packets,
  total_fwd_bytes, total_bwd_bytes, flow_bytes_per_sec, flow_packets_per_sec,
  syn_flag_count, rst_flag_count, avg_packet_size

Training strategy: fit Isolation Forest ONLY on BENIGN flows so the model
learns what "normal" looks like; anomalous flows are flagged as deviations.
"""

import glob
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_PATH = "ids_model.joblib"
DATA_DIR = "data"

FEATURES = [
    "destination_port",
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

# Column names in CICIDS2017 MachineLearningCSV (after strip) → feature names
CICIDS_COL_MAP = {
    "Destination Port":             "destination_port",
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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_cicids2017(data_dir: str) -> pd.DataFrame | None:
    csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    csv_files += glob.glob(os.path.join(data_dir, "*.csv"))
    csv_files = sorted(set(csv_files))

    if not csv_files:
        return None

    print(f"Found {len(csv_files)} CICIDS2017 file(s):")
    dfs = []
    for path in csv_files:
        try:
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip()
            dfs.append(df)
            print(f"  {os.path.basename(path):55s}  {len(df):>9,} rows")
        except Exception as exc:
            print(f"  [WARN] Could not read {os.path.basename(path)}: {exc}")

    if not dfs:
        return None

    combined = pd.concat(dfs, ignore_index=True)
    print(f"Total rows loaded: {len(combined):,}")
    return combined


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def preprocess_cicids(df: pd.DataFrame, max_benign: int = 300_000) -> np.ndarray:
    needed = list(CICIDS_COL_MAP.keys())
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}\nAvailable: {list(df.columns[:20])}"
        )

    df = df[needed].copy()
    df.rename(columns=CICIDS_COL_MAP, inplace=True)
    df["label"] = df["label"].astype(str).str.strip()

    # Flow Duration in CICIDS2017 is in microseconds → convert to seconds
    df["flow_duration"] = df["flow_duration"] / 1_000_000.0

    # Replace Inf/-Inf (common for Flow Bytes/s when duration == 0)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(df)
    df.dropna(subset=FEATURES, inplace=True)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with NaN/Inf")

    df = df[df["flow_duration"] > 0].copy()

    # Label distribution
    counts = df["label"].value_counts()
    print("\nLabel distribution (after cleaning):")
    for lbl, cnt in counts.items():
        pct = cnt / len(df) * 100
        print(f"  {lbl:<40} {cnt:>9,}  ({pct:5.1f}%)")

    # Keep only BENIGN for training
    benign = df[df["label"] == "BENIGN"]
    print(f"\nBENIGN rows available for training: {len(benign):,}")

    if len(benign) < 1_000:
        raise ValueError(f"Too few BENIGN rows: {len(benign)}")

    # Sample to keep training time reasonable (IF scales as O(n·trees))
    if len(benign) > max_benign:
        benign = benign.sample(max_benign, random_state=42)
        print(f"Sampled {max_benign:,} BENIGN rows for training")

    # Cap extreme values at 99.9th percentile to reduce scaler distortion
    X = benign[FEATURES].copy()
    for col in ["flow_bytes_per_sec", "flow_packets_per_sec",
                "total_fwd_packets", "total_bwd_packets",
                "total_fwd_bytes", "total_bwd_bytes"]:
        cap = X[col].quantile(0.999)
        X[col] = X[col].clip(upper=cap)

    return X.values.astype(np.float64)


# ---------------------------------------------------------------------------
# Synthetic fallback (used when no CICIDS2017 files are found)
# ---------------------------------------------------------------------------

def generate_synthetic_data(n_normal: int = 8_000, n_anomaly: int = 600) -> np.ndarray:
    print("No CICIDS2017 data found — generating synthetic training data.")
    rng = np.random.default_rng(42)
    k = n_anomaly // 3

    def normal(n):
        return np.column_stack([
            rng.choice([80, 443, 53, 22, 8080, 3306, 5432], n),
            rng.uniform(0.1, 60.0, n),
            rng.integers(1, 120, n),
            rng.integers(1, 120, n),
            rng.integers(100, 60_000, n),
            rng.integers(100, 60_000, n),
            rng.uniform(100, 60_000, n),
            rng.uniform(0.1, 10.0, n),
            rng.integers(0, 2, n),
            rng.integers(0, 1, n),
            rng.uniform(100, 1_000, n),
        ])

    port_scan = np.column_stack([
        rng.integers(1, 65535, k),
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

    return np.vstack([normal(n_normal), port_scan, dos, brute])


# ---------------------------------------------------------------------------
# Train / load
# ---------------------------------------------------------------------------

def train_model(data_dir: str = DATA_DIR) -> Pipeline:
    df = load_cicids2017(data_dir)

    if df is not None:
        print("\nPreprocessing CICIDS2017 dataset...")
        X_train = preprocess_cicids(df)
        contamination = 0.01
        source = "CICIDS2017"
    else:
        X_train = generate_synthetic_data()
        contamination = 0.08
        source = "synthetic"

    print(f"\nTraining Isolation Forest on {len(X_train):,} {source} samples "
          f"({len(FEATURES)} features, contamination={contamination})...")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", IsolationForest(
            n_estimators=200,
            max_samples=min(len(X_train), 512),
            contamination=contamination,
            random_state=42,
            n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved → {MODEL_PATH}")
    return pipeline


def load_or_train(data_dir: str = DATA_DIR) -> Pipeline:
    if os.path.exists(MODEL_PATH):
        print(f"Loading saved model from {MODEL_PATH}")
        return joblib.load(MODEL_PATH)
    return train_model(data_dir)


# ---------------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------------

def predict(pipeline: Pipeline, features: list) -> dict:
    X = np.array(features, dtype=np.float64).reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=0.0)

    raw_score = pipeline.decision_function(X)[0]
    is_anomaly = pipeline.predict(X)[0] == -1

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
