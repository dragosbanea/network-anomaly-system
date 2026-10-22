"""
AI service — FastAPI server exposing the IDS model.
Start: python main.py  (listens on :5000)

To use CICIDS2017: place CSV files in ai/data/ before starting.
"""

import argparse
import json
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
from model import (load_or_train, load_if_model, train_model, predict, predict_if,
                   FEATURES, FEATURES_BASE, DATA_DIR, METRICS_PATH)

app = FastAPI(title="IDS AI Service", version="3.0.0")
pipeline = None
if_pipeline = None  # Secondary: Isolation Forest for unknown anomaly detection


class PredictRequest(BaseModel):
    # Base 11 features (required)
    destinationPort: int
    flowDuration: float
    totalFwdPackets: int
    totalBwdPackets: int
    totalFwdBytes: int
    totalBwdBytes: int
    flowBytesPerSec: float
    flowPacketsPerSec: float
    synFlagCount: int
    rstFlagCount: int
    avgPacketSize: float
    finFlagCount: int = 0
    ackFlagCount: int = 0
    pshFlagCount: int = 0
    urgFlagCount: int = 0
    fwdPacketLenMin: float = 0.0
    fwdPacketLenMax: float = 0.0
    bwdPacketLenMax: float = 0.0
    packetLenStd: float = 0.0


class PredictResponse(BaseModel):
    anomaly: bool
    anomalyScore: float
    confidence: float
    label: str


@app.on_event("startup")
async def startup():
    global pipeline, if_pipeline
    pipeline = load_or_train(DATA_DIR)
    if_pipeline = load_if_model()
    if if_pipeline is not None:
        print("Hybrid mode: RF (primary) + IsolationForest (secondary) loaded.")
    else:
        print("AI service ready (RF only — no IF model found).")


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    features = [
        req.destinationPort,
        req.flowDuration,
        req.totalFwdPackets,
        req.totalBwdPackets,
        req.totalFwdBytes,
        req.totalBwdBytes,
        req.flowBytesPerSec,
        req.flowPacketsPerSec,
        req.synFlagCount,
        req.rstFlagCount,
        req.avgPacketSize,
        req.finFlagCount,
        req.ackFlagCount,
        req.pshFlagCount,
        req.urgFlagCount,
        req.fwdPacketLenMin,
        req.fwdPacketLenMax,
        req.bwdPacketLenMax,
        req.packetLenStd,
    ]
    result = predict(pipeline, features)

    # Hybrid layer: if RF says BENIGN, run IF to catch unknown anomalies
    if not result["anomaly"] and if_pipeline is not None:
        if_result = predict_if(if_pipeline, features)
        if if_result["is_anomaly"]:
            return PredictResponse(
                anomaly=True,
                anomalyScore=if_result["anomaly_score"],
                confidence=if_result["confidence"],
                label="UNKNOWN",
            )

    return PredictResponse(**result)


@app.post("/train")
def retrain(data_dir: str = DATA_DIR):
    global pipeline
    pipeline = train_model(data_dir)
    return {"status": "Model retrained successfully"}


@app.get("/health")
def health():
    return {"status": "ok", "modelLoaded": pipeline is not None}


@app.get("/metrics")
def get_metrics():
    if not os.path.exists(METRICS_PATH):
        raise HTTPException(
            status_code=404,
            detail="No metrics file found. Run: python model.py --compare"
        )
    with open(METRICS_PATH) as f:
        return json.load(f)


@app.get("/model/info")
def model_info():
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    model_step = pipeline.named_steps["model"]
    n_features = getattr(model_step, "n_features_in_", len(FEATURES_BASE))
    if isinstance(model_step, IsolationForest):
        return {
            "type": "IsolationForest",
            "nEstimators": model_step.n_estimators,
            "contamination": model_step.contamination,
            "nFeatures": n_features,
            "features": FEATURES[:n_features],
        }
    return {
        "type": "RandomForest",
        "nEstimators": model_step.n_estimators,
        "classes": list(model_step.classes_),
        "nFeatures": n_features,
        "features": FEATURES[:n_features],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--retrain", action="store_true",
                        help="Force retrain even if a saved model exists")
    args = parser.parse_args()

    if args.retrain:
        from model import MODEL_PATH, RF_MODEL_PATH
        for p in (MODEL_PATH, RF_MODEL_PATH):
            if os.path.exists(p):
                os.remove(p)
                print(f"Deleted existing model ({p}) — will retrain.")

    uvicorn.run(app, host=args.host, port=args.port)
