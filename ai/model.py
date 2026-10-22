"""
Anomaly detection model trained on CICIDS2017 (MachineLearningCSV variant).

Feature set — 19 features matching CICFlowMeter output:
  Base (11): destination_port, flow_duration, total_fwd_packets, total_bwd_packets,
             total_fwd_bytes, total_bwd_bytes, flow_bytes_per_sec, flow_packets_per_sec,
             syn_flag_count, rst_flag_count, avg_packet_size
  Extended (8): fin_flag_count, ack_flag_count, psh_flag_count, urg_flag_count,
                fwd_packet_len_min, fwd_packet_len_max, bwd_packet_len_max, packet_len_std

Three models trained and compared:
  - Isolation Forest  (unsupervised, BENIGN-only training)
  - One-Class SVM     (semi-supervised, BENIGN-only training)
  - Random Forest     (supervised, all labeled data)

The primary deployed model is Random Forest (ids_model_rf.joblib).
Run  python model.py --compare  to train and benchmark all three.
"""

import argparse
import glob
import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (classification_report, f1_score,
                              precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

MODEL_PATH     = "ids_model.joblib"
RF_MODEL_PATH  = "ids_model_rf.joblib"
SVM_MODEL_PATH = "ids_model_svm.joblib"
METRICS_PATH   = "model_metrics.json"
DATA_DIR       = "data"

FEATURES_BASE = [
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

FEATURES_EXT = [
    "fin_flag_count",
    "ack_flag_count",
    "psh_flag_count",
    "urg_flag_count",
    "fwd_packet_len_min",
    "fwd_packet_len_max",
    "bwd_packet_len_max",
    "packet_len_std",
]

FEATURES = FEATURES_BASE + FEATURES_EXT  # 19 total

CICIDS_COL_MAP = {
    # Base
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
    # Extended
    "FIN Flag Count":               "fin_flag_count",
    "ACK Flag Count":               "ack_flag_count",
    "PSH Flag Count":               "psh_flag_count",
    "URG Flag Count":               "urg_flag_count",
    "Fwd Packet Length Min":        "fwd_packet_len_min",
    "Fwd Packet Length Max":        "fwd_packet_len_max",
    "Bwd Packet Length Max":        "bwd_packet_len_max",
    "Packet Length Std":            "packet_len_std",
    "Label":                        "label",
}



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



def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Rename all available mapped columns in-place
    rename_map = {k: v for k, v in CICIDS_COL_MAP.items() if k in df.columns}
    df.rename(columns=rename_map, inplace=True)

    # Verify required base features exist
    missing_base = [f for f in FEATURES_BASE + ["label"] if f not in df.columns]
    if missing_base:
        raise ValueError(
            f"Missing required columns: {missing_base}\nAvailable: {list(df.columns[:20])}"
        )

    missing_ext = [f for f in FEATURES_EXT if f not in df.columns]
    if missing_ext:
        print(f"  [INFO] Extended features absent in CSV, padding with 0: {missing_ext}")
        for feat in missing_ext:
            df[feat] = 0

    df = df[FEATURES + ["label"]].copy()
    df["label"] = df["label"].astype(str).str.strip()
    df["flow_duration"] = df["flow_duration"] / 1_000_000.0
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(df)
    df.dropna(subset=FEATURES, inplace=True)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with NaN/Inf")
    df = df[df["flow_duration"] > 0].copy()
    return df


def _cap_extremes(X: pd.DataFrame) -> pd.DataFrame:
    cols_to_cap = [
        "flow_bytes_per_sec", "flow_packets_per_sec",
        "total_fwd_packets", "total_bwd_packets",
        "total_fwd_bytes", "total_bwd_bytes",
        "fwd_packet_len_max", "bwd_packet_len_max",
        "packet_len_std",
    ]
    for col in cols_to_cap:
        if col in X.columns:
            cap = X[col].quantile(0.999)
            X[col] = X[col].clip(upper=cap)
    return X


def _print_distribution(df: pd.DataFrame) -> None:
    counts = df["label"].value_counts()
    print("\nLabel distribution:")
    for lbl, cnt in counts.items():
        pct = cnt / len(df) * 100
        print(f"  {lbl:<40} {cnt:>9,}  ({pct:5.1f}%)")


def preprocess_for_anomaly(df: pd.DataFrame, max_benign: int = 300_000) -> np.ndarray:
    benign = df[df["label"] == "BENIGN"]
    print(f"\nBENIGN rows available for training: {len(benign):,}")
    if len(benign) < 1_000:
        raise ValueError(f"Too few BENIGN rows: {len(benign)}")
    if len(benign) > max_benign:
        benign = benign.sample(max_benign, random_state=42)
        print(f"Sampled {max_benign:,} BENIGN rows for training")
    X = _cap_extremes(benign[FEATURES].copy())
    return X.values.astype(np.float64)


def preprocess_for_supervised(
    df: pd.DataFrame, test_size: float = 0.2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X = _cap_extremes(df[FEATURES].copy())
    y = df["label"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X.values.astype(np.float64), y,
        test_size=test_size, random_state=42, stratify=y,
    )
    print(f"\nTrain: {len(X_train):,} rows | Test: {len(X_test):,} rows")
    return X_train, X_test, y_train, y_test


def preprocess_cicids(df: pd.DataFrame, max_benign: int = 300_000) -> np.ndarray:
    df = _clean_df(df)
    _print_distribution(df)
    return preprocess_for_anomaly(df, max_benign)



def _train_isolation_forest(X_train: np.ndarray, contamination: float = 0.01) -> Pipeline:
    print(f"\nTraining Isolation Forest on {len(X_train):,} BENIGN samples "
          f"(contamination={contamination})...")
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
    return pipeline


def _train_one_class_svm(X_train: np.ndarray, max_samples: int = 5_000) -> Pipeline:
    if len(X_train) > max_samples:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(X_train), max_samples, replace=False)
        X_fit = X_train[idx]
        print(f"\nTraining One-Class SVM on {max_samples:,} BENIGN samples "
              f"(subsampled from {len(X_train):,})...")
    else:
        X_fit = X_train
        print(f"\nTraining One-Class SVM on {len(X_fit):,} BENIGN samples...")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", OneClassSVM(kernel="rbf", nu=0.01, gamma="scale")),
    ])
    pipeline.fit(X_fit)
    return pipeline


def _train_random_forest(X_train: np.ndarray, y_train: np.ndarray) -> Pipeline:
    print(f"\nTraining Random Forest on {len(X_train):,} labeled samples "
          f"({X_train.shape[1]} features)...")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )),
    ])
    pipeline.fit(X_train, y_train)
    return pipeline



def _binary_labels(y: np.ndarray) -> np.ndarray:
    return (y != "BENIGN").astype(int)


def evaluate_anomaly_model(
    pipeline: Pipeline, X_test: np.ndarray, y_test: np.ndarray, name: str
) -> dict:
    n_model = getattr(pipeline.named_steps["model"], "n_features_in_", X_test.shape[1])
    X_eval = X_test[:, :n_model]
    preds = pipeline.predict(X_eval)
    y_pred_binary = (preds == -1).astype(int)
    y_true_binary = _binary_labels(y_test)
    prec = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    rec  = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1   = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    print(f"\n--- {name} ---")
    print(f"  Precision: {prec:.4f}  Recall: {rec:.4f}  F1: {f1:.4f}")
    return {"precision": prec, "recall": rec, "f1": f1}


def evaluate_rf_model(
    pipeline: Pipeline, X_test: np.ndarray, y_test: np.ndarray
) -> tuple[dict, dict]:
    y_pred = pipeline.predict(X_test)
    print("\n--- Random Forest (per-class report) ---")
    print(classification_report(y_test, y_pred, zero_division=0))
    per_class_raw = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
    y_pred_binary = _binary_labels(y_pred)
    y_true_binary = _binary_labels(y_test)
    prec = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    rec  = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1   = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    print(f"  Binary — Precision: {prec:.4f}  Recall: {rec:.4f}  F1: {f1:.4f}")
    return {"precision": prec, "recall": rec, "f1": f1}, per_class_raw


def _save_metrics(if_metrics: dict, svm_metrics: dict, rf_metrics: dict,
                  rf_per_class_raw: dict, n_features: int,
                  n_train: int, n_test: int) -> None:
    skip_keys = {"accuracy", "macro avg", "weighted avg"}
    clean_per_class = {
        label: {
            "precision": round(v["precision"], 4),
            "recall":    round(v["recall"], 4),
            "f1":        round(v["f1-score"], 4),
            "support":   int(v["support"]),
        }
        for label, v in rf_per_class_raw.items()
        if label not in skip_keys and isinstance(v, dict)
    }

    data = {
        "trainedAt":    datetime.now().isoformat(),
        "nFeatures":    n_features,
        "featuresBase": FEATURES_BASE,
        "featuresExt":  FEATURES_EXT,
        "nSamplesTrain": int(n_train),
        "nSamplesTest":  int(n_test),
        "models": {
            "RandomForest": {
                "precision": round(rf_metrics["precision"], 4),
                "recall":    round(rf_metrics["recall"], 4),
                "f1":        round(rf_metrics["f1"], 4),
                "perClass":  clean_per_class,
            },
            "IsolationForest": {
                "precision": round(if_metrics["precision"], 4),
                "recall":    round(if_metrics["recall"], 4),
                "f1":        round(if_metrics["f1"], 4),
            },
            "OneClassSVM": {
                "precision": round(svm_metrics["precision"], 4),
                "recall":    round(svm_metrics["recall"], 4),
                "f1":        round(svm_metrics["f1"], 4),
            },
        },
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nMetrics saved → {METRICS_PATH}")


# ---------------------------------------------------------------------------
# Train all three models and compare
# ---------------------------------------------------------------------------

def train_all_models(data_dir: str = DATA_DIR):
    df = load_cicids2017(data_dir)
    if df is None:
        raise RuntimeError("No CICIDS2017 data found in data/")

    print("\nPreprocessing CICIDS2017 dataset...")
    df = _clean_df(df)
    _print_distribution(df)

    X_train_sup, X_test, y_train_sup, y_test = preprocess_for_supervised(df)
    X_train_anom = preprocess_for_anomaly(df)

    if_pipeline  = _train_isolation_forest(X_train_anom, contamination=0.01)
    svm_pipeline = _train_one_class_svm(X_train_anom)
    rf_pipeline  = _train_random_forest(X_train_sup, y_train_sup)

    print("\n" + "=" * 60)
    print("MODEL COMPARISON ON CICIDS2017 TEST SET")
    print("=" * 60)
    if_metrics  = evaluate_anomaly_model(if_pipeline,  X_test, y_test, "Isolation Forest")
    svm_metrics = evaluate_anomaly_model(svm_pipeline, X_test, y_test, "One-Class SVM")
    rf_metrics, rf_per_class = evaluate_rf_model(rf_pipeline, X_test, y_test)

    print("\n" + "=" * 60)
    print(f"{'Model':<22} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-" * 60)
    for name, m in [("Isolation Forest", if_metrics),
                    ("One-Class SVM",    svm_metrics),
                    ("Random Forest",    rf_metrics)]:
        print(f"{name:<22} {m['precision']:>10.4f} {m['recall']:>10.4f} {m['f1']:>10.4f}")
    print("=" * 60)

    _save_metrics(if_metrics, svm_metrics, rf_metrics, rf_per_class,
                  n_features=len(FEATURES),
                  n_train=len(X_train_sup),
                  n_test=len(X_test))

    joblib.dump(if_pipeline,  MODEL_PATH)
    joblib.dump(rf_pipeline,  RF_MODEL_PATH)
    joblib.dump(svm_pipeline, SVM_MODEL_PATH)
    print(f"\nModels saved: {MODEL_PATH}, {RF_MODEL_PATH}, {SVM_MODEL_PATH}")
    return if_pipeline, rf_pipeline, svm_pipeline



def train_model(data_dir: str = DATA_DIR) -> Pipeline:
    df = load_cicids2017(data_dir)
    if df is not None:
        print("\nPreprocessing CICIDS2017 dataset...")
        df = _clean_df(df)
        _print_distribution(df)
        X = _cap_extremes(df[FEATURES].copy()).values.astype(np.float64)
        y = df["label"].values
        pipeline = _train_random_forest(X, y)
        joblib.dump(pipeline, RF_MODEL_PATH)
        print(f"Model saved → {RF_MODEL_PATH}")
        return pipeline
    else:
        X_train = generate_synthetic_data()
        pipeline = _train_isolation_forest(X_train, contamination=0.08)
        joblib.dump(pipeline, MODEL_PATH)
        return pipeline


def load_or_train(data_dir: str = DATA_DIR) -> Pipeline:
    if os.path.exists(RF_MODEL_PATH):
        print(f"Loading saved RF model from {RF_MODEL_PATH}")
        return joblib.load(RF_MODEL_PATH)
    if os.path.exists(MODEL_PATH):
        print(f"Loading saved IF model from {MODEL_PATH}")
        return joblib.load(MODEL_PATH)
    return train_model(data_dir)



def generate_synthetic_data(n_normal: int = 8_000, n_anomaly: int = 600) -> np.ndarray:
    print("No CICIDS2017 data found — generating synthetic training data.")
    rng = np.random.default_rng(42)
    k = n_anomaly // 3

    def _ext_normal(n):
        return np.column_stack([
            rng.integers(0, 3, n),      # fin_flag_count
            rng.integers(1, 20, n),     # ack_flag_count
            rng.integers(0, 5, n),      # psh_flag_count
            rng.integers(0, 1, n),      # urg_flag_count
            rng.uniform(40, 300, n),    # fwd_packet_len_min
            rng.uniform(400, 1500, n),  # fwd_packet_len_max
            rng.uniform(40, 1500, n),   # bwd_packet_len_max
            rng.uniform(50, 400, n),    # packet_len_std
        ])

    def normal(n):
        base = np.column_stack([
            rng.choice([80, 443, 53, 22, 8080, 3306, 5432], n),
            rng.uniform(0.1, 60.0, n),
            rng.integers(1, 120, n), rng.integers(1, 120, n),
            rng.integers(100, 60_000, n), rng.integers(100, 60_000, n),
            rng.uniform(100, 60_000, n), rng.uniform(0.1, 10.0, n),
            rng.integers(0, 2, n), rng.integers(0, 1, n),
            rng.uniform(100, 1_000, n),
        ])
        return np.hstack([base, _ext_normal(n)])

    port_scan = np.column_stack([
        rng.integers(1, 65535, k), rng.uniform(0.001, 0.1, k),
        rng.integers(1, 3, k), rng.integers(0, 1, k),
        rng.integers(40, 200, k), rng.integers(0, 100, k),
        rng.uniform(1_000, 100_000, k), rng.uniform(100, 1_500, k),
        rng.integers(1, 4, k), rng.integers(0, 3, k), rng.uniform(40, 100, k),
        rng.integers(1, 3, k), rng.integers(0, 2, k), rng.integers(0, 1, k),
        rng.integers(0, 1, k),
        rng.uniform(40, 80, k), rng.uniform(60, 120, k),
        rng.uniform(0, 100, k), rng.uniform(5, 30, k),
    ])
    dos = np.column_stack([
        rng.choice([80, 443], k), rng.uniform(0.001, 2.0, k),
        rng.integers(1_000, 50_000, k), rng.integers(0, 100, k),
        rng.integers(1_000_000, 50_000_000, k), rng.integers(0, 10_000, k),
        rng.uniform(500_000, 5_000_000, k), rng.uniform(1_000, 10_000, k),
        rng.integers(0, 5, k), rng.integers(0, 5, k), rng.uniform(50, 150, k),
        rng.integers(0, 2, k), rng.integers(1_000, 5_000, k), rng.integers(0, 2, k),
        rng.integers(0, 1, k),
        rng.uniform(40, 80, k), rng.uniform(60, 150, k),
        rng.uniform(40, 200, k), rng.uniform(10, 50, k),
    ])
    brute = np.column_stack([
        rng.choice([22, 3389, 21, 23], k), rng.uniform(10, 600, k),
        rng.integers(50, 500, k), rng.integers(50, 500, k),
        rng.integers(5_000, 200_000, k), rng.integers(5_000, 200_000, k),
        rng.uniform(100, 2_000, k), rng.uniform(0.5, 5.0, k),
        rng.integers(1, 5, k), rng.integers(0, 3, k), rng.uniform(100, 500, k),
        rng.integers(0, 2, k), rng.integers(1, 10, k), rng.integers(0, 1, k),
        rng.integers(0, 1, k),
        rng.uniform(40, 200, k), rng.uniform(200, 600, k),
        rng.uniform(40, 600, k), rng.uniform(50, 200, k),
    ])
    return np.vstack([normal(n_normal), port_scan, dos, brute])



def _is_isolation_forest(pipeline: Pipeline) -> bool:
    return isinstance(pipeline.named_steps.get("model"), IsolationForest)


_INFERENCE_CAPS = {
    2: 2_000.0,       # flow_bytes_per_sec  (index in FEATURES)
    # index 0=destination_port,1=flow_duration,2=total_fwd_packets …
}
_CAP_MAP = {
    "flow_bytes_per_sec":    (FEATURES.index("flow_bytes_per_sec"),    4_000_000.0),
    "flow_packets_per_sec":  (FEATURES.index("flow_packets_per_sec"),  250_000.0),
    "total_fwd_packets":     (FEATURES.index("total_fwd_packets"),     10_000.0),
    "total_bwd_packets":     (FEATURES.index("total_bwd_packets"),     10_000.0),
    "total_fwd_bytes":       (FEATURES.index("total_fwd_bytes"),       5_000_000.0),
    "total_bwd_bytes":       (FEATURES.index("total_bwd_bytes"),       5_000_000.0),
    "fwd_packet_len_max":    (FEATURES.index("fwd_packet_len_max"),    1_500.0),
    "bwd_packet_len_max":    (FEATURES.index("bwd_packet_len_max"),    1_500.0),
    "packet_len_std":        (FEATURES.index("packet_len_std"),        500.0),
}


def predict(pipeline: Pipeline, features: list) -> dict:
    model_step = pipeline.named_steps.get("model")
    n_expected = getattr(model_step, "n_features_in_", len(FEATURES))
    features_in = features[:n_expected]

    X = np.array(features_in, dtype=np.float64).reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=0.0)


    for idx, cap in _CAP_MAP.values():
        if idx < X.shape[1]:
            X[0, idx] = min(X[0, idx], cap)

    if _is_isolation_forest(pipeline):
        raw_score = pipeline.decision_function(X)[0]
        is_anomaly = pipeline.predict(X)[0] == -1
        anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
        confidence = float(np.clip(abs(raw_score) * 2, 0.0, 1.0))
        return {
            "anomaly": bool(is_anomaly),
            "anomalyScore": round(anomaly_score, 4),
            "confidence": round(confidence, 4),
            "label": "ANOMALY" if is_anomaly else "NORMAL",
        }

    predicted_class = str(pipeline.predict(X)[0])
    is_anomaly = predicted_class != "BENIGN"
    proba = pipeline.predict_proba(X)[0]
    classes = list(pipeline.named_steps["model"].classes_)
    benign_idx = classes.index("BENIGN")
    benign_prob = float(proba[benign_idx])
    anomaly_score = round(float(np.clip(1.0 - benign_prob, 0.0, 1.0)), 4)
    confidence = round(float(max(proba)), 4)
    return {
        "anomaly": is_anomaly,
        "anomalyScore": anomaly_score,
        "confidence": confidence,
        "label": predicted_class if is_anomaly else "NORMAL",
    }


def load_if_model() -> Pipeline | None:
    if os.path.exists(MODEL_PATH):
        print(f"Loading saved IF model from {MODEL_PATH}")
        return joblib.load(MODEL_PATH)
    return None


def predict_if(if_pipeline: Pipeline, features: list) -> dict:
    """Run Isolation Forest on the same feature vector. Returns anomaly flag and score."""
    n_expected = getattr(if_pipeline.named_steps.get("model"), "n_features_in_", len(FEATURES))
    features_in = features[:n_expected]
    X = np.array(features_in, dtype=np.float64).reshape(1, -1)
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=0.0)
    for idx, cap in _CAP_MAP.values():
        if idx < X.shape[1]:
            X[0, idx] = min(X[0, idx], cap)
    raw_score = if_pipeline.decision_function(X)[0]
    is_anomaly = if_pipeline.predict(X)[0] == -1
    anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
    confidence = float(np.clip(abs(raw_score) * 2, 0.0, 1.0))
    return {
        "is_anomaly": bool(is_anomaly),
        "anomaly_score": round(anomaly_score, 4),
        "confidence": round(confidence, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IDS model training")
    parser.add_argument("--compare", action="store_true",
                        help="Train all three models and print comparison table")
    parser.add_argument("--data-dir", default=DATA_DIR)
    args = parser.parse_args()
    if args.compare:
        train_all_models(args.data_dir)
    else:
        train_model(args.data_dir)
