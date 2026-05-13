"""
AI service — FastAPI server exposing the Isolation Forest model.
Start: python main.py  (listens on :5000)

To use CICIDS2017: place CSV files in ai/data/ before starting.
"""

import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from model import load_or_train, train_model, predict, FEATURES, DATA_DIR

app = FastAPI(title="IDS AI Service", version="2.0.0")
pipeline = None


class PredictRequest(BaseModel):
    destinationPort: int
    flowDuration: float         # seconds
    totalFwdPackets: int
    totalBwdPackets: int
    totalFwdBytes: int
    totalBwdBytes: int
    flowBytesPerSec: float
    flowPacketsPerSec: float
    synFlagCount: int
    rstFlagCount: int
    avgPacketSize: float


class PredictResponse(BaseModel):
    anomaly: bool
    anomalyScore: float
    confidence: float
    label: str


@app.on_event("startup")
async def startup():
    global pipeline
    pipeline = load_or_train(DATA_DIR)
    print("AI service ready.")


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
    ]
    return PredictResponse(**predict(pipeline, features))


@app.post("/train")
def retrain(data_dir: str = DATA_DIR):
    global pipeline
    pipeline = train_model(data_dir)
    return {"status": "Model retrained successfully"}


@app.get("/health")
def health():
    return {"status": "ok", "modelLoaded": pipeline is not None}


@app.get("/model/info")
def model_info():
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    iso = pipeline.named_steps["model"]
    return {
        "type": "IsolationForest",
        "nEstimators": iso.n_estimators,
        "contamination": iso.contamination,
        "features": FEATURES,
        "nFeatures": len(FEATURES),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--retrain", action="store_true",
                        help="Force retrain even if a saved model exists")
    args = parser.parse_args()

    if args.retrain:
        import os
        from model import MODEL_PATH
        if os.path.exists(MODEL_PATH):
            os.remove(MODEL_PATH)
            print(f"Deleted existing model ({MODEL_PATH}) — will retrain.")

    uvicorn.run(app, host=args.host, port=args.port)
