from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from typing import List, Dict
import numpy as np

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Load telemetry data CSV at startup
data_path = "q-vercel-latency.json"  # Assuming you convert JSON to CSV, or load JSON directly with Pandas
# We'll parse JSON content to DataFrame at startup for example's sake:
import json
with open(data_path) as f:
    json_data = json.load(f)
# Convert JSON list to DataFrame (assuming json_data is a list of dicts)
df = pd.DataFrame(json_data)

# Rename columns or normalize keys if needed, e.g. lower-cased, e.g., 'region', 'latencyms', 'uptimepct'


class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

@app.post("/latency-metrics")
async def latency_metrics(req: MetricsRequest):
    # Filter data by requested regions
    filtered = df[df["region"].str.lower().isin([r.lower() for r in req.regions])]

    results: Dict[str, Dict[str, float]] = {}

    for region in req.regions:
        region_data = filtered[filtered["region"].str.lower() == region.lower()]

        # Defensive in case no data for region
        if region_data.empty:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0,
            }
            continue

        latencies = region_data["latencyms"]

        avg_latency = latencies.mean()
        p95_latency = np.percentile(latencies, 95)
        avg_uptime = region_data["uptimepct"].mean()
        breaches = (latencies > req.threshold_ms).sum()

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": int(breaches),
        }

    return results
