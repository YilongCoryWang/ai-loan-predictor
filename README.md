# Loan Prediction System

A machine learning application for loan approval prediction using FastAPI</p>

## 📋 Overview

This repository contains a complete loan prediction system that combines:
- Jupyter notebook for model training and evaluation
- FastAPI service for real-time predictions
- Docker support for easy deployment

## 📁 Project Structure

```
loan/
├── trainer.ipynb      # Model training and evaluation
├── main.py           # FastAPI application
├── loan.csv          # Training dataset
├── loan_model.pkl    # Trained SVM model
├── loan_scaler.pkl   # Feature scaler
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container configuration
├── static/           # Frontend files
└── start.sh          # Startup script
```

## 🔍 Key Components

### Model Training (trainer.ipynb)
- **Data Processing**: Handles missing values, encodes categorical features, and scales numerical data
- **Model Evaluation**: Compares multiple algorithms (Logistic Regression, SVC, KNN, Random Forest)
- **Hyperparameter Tuning**: Optimizes SVM model for best performance
- **Model Export**: Saves trained model and scaler for deployment

### Prediction API (main.py)
- **FastAPI Setup**: RESTful API with CORS and logging configuration
- **Model Integration**: Efficient loading of ML artifacts using lifespan context
- **Data Validation**: Strict input validation with Pydantic models
- **Prediction Endpoint**: `/predict_loan_status` for loan approval predictions

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
bash start.sh
# or
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t loan-prediction .
docker run -p 8000:8000 loan-prediction
```

## 🔧 API Usage

### Make a Prediction
Send a POST request to `/predict_loan_status`:

```json
{
  "Gender": 1, "Married": 1, "Dependents": 0,
  "Education": 1, "Self_Employed": 0,
  "ApplicantIncome": 5000, "CoapplicantIncome": 0.0,
  "LoanAmount": 150.0, "Loan_Amount_Term": 360.0,
  "Credit_History": 1.0, "Property_Area": 2
}
```

### Response Format
```json
{
  "loan_status": "Approved",
  "confidence": 0.75
}
```

## 📚 Documentation
- API documentation: http://localhost:8000/docs
- Interactive UI: http://localhost:8000

## 🎯 Features
- 🔒 Input validation with Pydantic
- 📊 Multiple model comparison
- ⚡ FastAPI for high performance
- 🐳 Containerized deployment
- 📝 Comprehensive logging

## 📄 License
For educational purposes