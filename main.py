"""
贷款预测API服务

此模块提供了一个FastAPI应用程序，用于预测贷款申请的批准状态。
应用程序加载预训练的模型和缩放器，并通过RESTful端点提供预测服务。
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import logging
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from features import LoanFeatures, FEATURE_NAMES

model = None
scaler = None
log = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    应用程序生命周期管理器

    负责在应用启动时加载模型和缩放器，在应用关闭时执行清理操作。

    Args:
        _app: FastAPI应用实例（未使用但符合上下文管理器接口要求）
    """
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
    """
    首页端点

    返回应用程序的静态HTML首页。

    Returns:
        FileResponse: 包含HTML首页的文件响应
    """
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
