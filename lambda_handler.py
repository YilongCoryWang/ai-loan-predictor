import pandas as pd
import logging
import os
import joblib
import json
from features import FEATURE_NAMES

model = None
scaler = None
# 使用标准日志器
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def load_model():
    global model, scaler
    # 只有在模型未加载时才加载
    if model is None or scaler is None:
        try:
            model_path = os.getenv("MODEL_PATH", "loan_model.pkl")
            scaler_path = os.getenv("SCALER_PATH", "loan_scaler.pkl")
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            if model is None or scaler is None:
                raise ValueError("Model or scaler is None after loading.")

            log.info("Model and scaler loaded successfully.")

        except Exception as e:
            log.error(f"Error loading model or scaler: {e}")
            # 直接返回错误响应，而不是抛出HTTPException
            raise

def lambda_handler(event, context):
    # 检查是否为API Gateway事件
    if 'body' in event:
        # 解析API Gateway请求体
        try:
            data = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON format'})
            }
    else:
        # 直接Lambda调用
        data = event
    
    # 处理预测逻辑
    try:
        load_model()
        feature_dict = data
        feature_data = pd.DataFrame([feature_dict])

        data_for_scaling = feature_data[FEATURE_NAMES]
        log.info(f"Feature data for scaling: {data_for_scaling}")
        feature_data_scaled = scaler.transform(data_for_scaling)
        feature_data_scaled_df = pd.DataFrame(feature_data_scaled, columns=FEATURE_NAMES)

        is_approved = model.predict(feature_data_scaled_df)[0]
        log.info(f"Prediction result: {is_approved}")

        # 0 for Rejected, 1 for Approved
        prediction_result = 1 if is_approved else 0
        
        # 构建返回结果
        result = {
            "prediction": prediction_result,
            "message": "Loan Approved" if prediction_result == 1 else "Loan Rejected"
        }
        
        # 返回标准API Gateway响应格式
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # 允许跨域请求
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        log.error(f"Error processing prediction: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }