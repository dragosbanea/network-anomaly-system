from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from model import load_or_train, train_model, predict, FEATURES

app = FastAPI(title="IDS AI Service", version="1.0.0")
pipeline = None


class PredictRequest(BaseModel):
    packetCount: int
    byteCount: int
    duration: float
    protocol: int
    destinationPort: int
    connectionsPerSecond: float


class PredictResponse(BaseModel):
    anomaly: bool
    anomalyScore: float
    confidence: float
    label: str


@app.on_event("startup")
async def startup():
    global pipeline
    pipeline = load_or_train()
    print("AI service ready.")


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    features = [
        req.packetCount,
        req.byteCount,
        req.duration,
        req.protocol,
        req.destinationPort,
        req.connectionsPerSecond,
    ]
    result = predict(pipeline, features)
    return PredictResponse(**result)


@app.post("/train")
def retrain():
    global pipeline
    pipeline = train_model()
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
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
