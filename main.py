from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import joblib
import pandas as pd
import logging
from dotenv import load_dotenv
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

model = None
scaler = None
log = logging.getLogger("uvicorn")


class LoanFeatures(BaseModel):
    """
    Defines the input features for the loan eligibility prediction model.
    """

    Gender: int
    Married: int
    Dependents: int
    Education: int
    Self_Employed: int
    ApplicantIncome: int
    CoapplicantIncome: float
    LoanAmount: float
    Loan_Amount_Term: float
    Credit_History: float
    Property_Area: int


FEATURE_NAMES = [
    "Gender",
    "Married",
    "Dependents",
    "Education",
    "Self_Employed",
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History",
    "Property_Area",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic (Runs BEFORE the application starts serving requests) ---
    try:
        global model, scaler
        model_path = os.getenv("MODEL_PATH", "loan_model.pkl")
        scaler_path = os.getenv("SCALER_PATH", "loan_scaler.pkl")
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        if model is None or scaler is None:
            raise ValueError("Model or scaler is None after loading.")

        log.info("Model and scaler loaded successfully.")

    except Exception as e:
        log.error(f"Error loading model or scaler: {e}")
        raise HTTPException(status_code=500, detail="Error loading model or scaler")

    yield  # <--- This is where the application becomes available to handle requests
    # shutdown logic
    log.info("Application shutdown...")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    html_file_path = os.path.join("static", "index.html")
    return FileResponse(html_file_path, media_type="text/html")


@app.post("/predict_loan_status")
async def predict_loan(features: LoanFeatures):
    """
    Accepts loan application features and returns the predicted loan status.

    Returns:
        {"prediction": 1} (Approved) or {"prediction": 0} (Rejected)
    """
    try:
        # 在实际应用中，您需要将 Pydantic 模型的字段转换为模型接受的格式 (如 NumPy 数组或 Pandas DataFrame)
        feature_dict = features.model_dump()
        feature_data = pd.DataFrame([feature_dict])

        global model, scaler, FEATURE_NAMES
        data_for_scaling = feature_data[FEATURE_NAMES]
        log.info(f"Feature data for scaling: {data_for_scaling}")
        feature_data_scaled = scaler.transform(data_for_scaling)
        feature_data_scaled_df = pd.DataFrame(feature_data_scaled, columns=feature_data.columns)

        is_approved = model.predict(feature_data_scaled_df)[0]
        log.info(f"Prediction result: {is_approved}")

        # 0 for Rejected, 1 for Approved
        prediction_result = 1 if is_approved else 0

        return {
            "prediction": prediction_result,
            "message": "Loan Approved" if prediction_result == 1 else "Loan Rejected",
        }

    except Exception as e:
        # 错误处理
        print(f"Prediction error: {e}")
        return {"error": "Prediction failed due to server error."}
