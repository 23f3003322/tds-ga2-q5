from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
from typing import List, Dict
import numpy as np
import json

app = FastAPI()

# Enable CORS for all origins, all methods, all headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Allow all origins
    allow_methods=["*"],   # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  
    expose_headers=["*"]    # Allow all headers
)

# Load your telemetry data JSON file (adjust path if needed)
data_path = Path(__file__).parent.parent / "q-vercel-latency.json"
with open(data_path) as f:
    json_data = json.load(f)
df = pd.DataFrame(json_data)
df.columns = df.columns.str.strip().str.lower()

class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.post("/api/latency")
async def latency_metrics(req: MetricsRequest):
    filtered = df[df["region"].str.lower().isin([r.lower() for r in req.regions])]

    results: Dict[str, Dict[str, float]] = {}
    for region in req.regions:
        region_data = filtered[filtered["region"].str.lower() == region.lower()]
        if region_data.empty:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0,
            }
            continue

        latencies = region_data["latency_ms"]
        avg_latency = latencies.mean()
        p95_latency = np.percentile(latencies, 95)
        avg_uptime = region_data["uptime_pct"].mean()
        breaches = (latencies > req.threshold_ms).sum()

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": int(breaches),
        }

    return {"regions": results}
