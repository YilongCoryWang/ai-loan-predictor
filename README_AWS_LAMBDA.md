# AWS Lambda 部署说明（Docker + ECR）

本文档详细介绍了如何使用Docker容器和Amazon ECR将贷款预测模型部署到AWS Lambda，使`predict_loan`函数能够作为无服务器函数调用。使用容器镜像部署适用于大型模型和依赖项。

## 准备工作

1. **安装AWS CLI**：确保您已安装并配置好AWS CLI。
2. **安装Docker**：确保Docker已安装并正在运行。
3. **准备模型文件**：确保`loan_model.pkl`和`loan_scaler.pkl`文件存在。
4. **准备Dockerfile**：确保项目中已包含Dockerfile。

## 部署步骤

### 1. 创建适合Lambda的Dockerfile

确保您的项目根目录中有一个名为`Dockerfile`的文件，内容如下：

```dockerfile
# 使用AWS官方的Lambda Python基础镜像（使用Python 3.13以匹配本地环境）
FROM public.ecr.aws/lambda/python:3.13

# 将工作目录设置为Lambda执行环境的标准目录
WORKDIR ${LAMBDA_TASK_ROOT}

# 复制必要的文件到容器
COPY lambda_handler.py .
COPY loan_model.pkl .
COPY loan_scaler.pkl .
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置Lambda函数的处理程序
CMD ["lambda_handler.lambda_handler"]
```

### 2. 构建Docker镜像

```bash
# 构建Docker镜像
docker build -t loan-prediction-lambda .
```

### 3. 本地测试Docker容器（可选）

在部署到AWS之前，您可以在本地测试Docker容器：

```bash
# 运行容器并映射端口
docker run -p 9000:8080 loan-prediction-lambda

# 在另一个终端中测试容器
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"Gender": 1, "Married": 1, "Dependents": 2, "Education": 1, "Self_Employed": 0, "ApplicantIncome": 5000, "CoapplicantIncome": 1000.0, "LoanAmount": 150.0, "Loan_Amount_Term": 360.0, "Credit_History": 1.0, "Property_Area": 2}'
```

### 4. 创建Amazon ECR仓库

```bash
# 设置变量
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # 替换为您的首选区域
ECR_REPOSITORY_NAME="loan-prediction-lambda"

# 创建ECR仓库
aws ecr create-repository \
    --repository-name $ECR_REPOSITORY_NAME \
    --image-scanning-configuration scanOnPush=true \
    --region $AWS_REGION
```

### 5. 推送Docker镜像到ECR

```bash
# 登录ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 标记镜像
docker tag loan-prediction-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest

# 推送镜像到ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest
```

### 6. 创建Lambda role
```bash
# 创建role
aws iam attach-role-policy --role-name lambda-exec-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### 7. 创建Lambda函数（使用容器镜像）

```bash
# 创建Lambda函数
aws lambda create-function \
    --function-name LoanPredictionFunction \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-role \
    --timeout 60 \
    --memory-size 512
```

**注意**：请将`YOUR_ACCOUNT_ID`替换为您的AWS账户ID，并确保已创建具有适当权限的IAM角色。

### 8. 配置Lambda环境变量（可选）

如果您希望自定义模型和缩放器的路径，可以设置以下环境变量：

```bash
aws lambda update-function-configuration \
    --function-name LoanPredictionFunction \
    --environment Variables={MODEL_PATH=loan_model.pkl,SCALER_PATH=loan_scaler.pkl}
```

### 9. 设置API Gateway（创建REST API）

为了能够通过HTTP调用您的Lambda函数，需要设置API Gateway：

```bash
# 创建REST API
aws apigateway create-rest-api --name "LoanPredictionAPI" --description "API for loan prediction"

# 记录API ID，然后获取根资源ID
API_ID="your-api-id"
ROOT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text)

# 创建/predict资源
aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_RESOURCE_ID --path-part "predict"

# 记录资源ID
RESOURCE_ID="your-resource-id"

# 创建POST方法
aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method POST --authorization-type "NONE"

# 集成Lambda（修正ARN格式）
aws apigateway put-integration --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method POST --type AWS_PROXY --integration-http-method POST --uri arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:LoanPredictionFunction/invocations

# 部署API
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod

# 添加Lambda权限（修正ARN格式）
aws lambda add-permission --function-name LoanPredictionFunction --statement-id apigateway --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:$AWS_REGION:$AWS_ACCOUNT_ID:$API_ID/*/POST/predict"
```

### 10. 测试API Gateway

**重要修复说明**：我们已经修复了以下两个关键问题：
1. API Gateway集成命令中的ARN格式错误
2. Lambda函数中的特征列名顺序问题

现在可以通过HTTP请求测试API是否正常工作：

#### 10.1 构建API调用URL

API调用URL的格式为：
```
https://{API_ID}.execute-api.{AWS_REGION}.amazonaws.com/prod/predict
```

请替换：
- `{API_ID}` 为您在步骤9中创建的API ID
- `{AWS_REGION}` 为您的AWS区域（如us-east-1）

#### 10.2 使用curl测试API

```bash
# 设置变量
API_ID="your-api-id"
AWS_REGION="us-east-1"

# 构建API URL
API_URL="https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod/predict"

# 使用curl发送POST请求
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"Gender": 1, "Married": 1, "Dependents": 2, "Education": 1, "Self_Employed": 0, "ApplicantIncome": 5000, "CoapplicantIncome": 1000.0, "LoanAmount": 150.0, "Loan_Amount_Term": 360.0, "Credit_History": 1.0, "Property_Area": 2}' \
  $API_URL
```

#### 10.3 使用Python脚本测试API

您也可以使用Python脚本测试API：

```python
import requests
import json

# 设置变量
api_id = "your-api-id"
aws_region = "us-east-1"

# 构建API URL
api_url = f"https://{api_id}.execute-api.{aws_region}.amazonaws.com/prod/predict"

# 准备测试数据
test_data = {
    "Gender": 1,
    "Married": 1,
    "Dependents": 2,
    "Education": 1,
    "Self_Employed": 0,
    "ApplicantIncome": 5000,
    "CoapplicantIncome": 1000.0,
    "LoanAmount": 150.0,
    "Loan_Amount_Term": 360.0,
    "Credit_History": 1.0,
    "Property_Area": 2
}

# 发送请求
response = requests.post(api_url, json=test_data)

# 打印响应
print("状态码:", response.status_code)
print("响应内容:", json.dumps(response.json(), indent=2))
```

#### 10.4 验证API Gateway响应格式

成功时，您将收到如下格式的响应：

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": "{\"prediction\": 1, \"message\": \"Loan Approved\"}"
}
```

#### 10.5 处理API Gateway格式的请求

请注意，当通过API Gateway调用Lambda函数时，传入的事件格式会包含API Gateway特定的字段。您的Lambda处理程序需要能够处理这种格式。确保您的`lambda_handler.py`文件包含适当的代码来解析API Gateway事件：

```python
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
    # ...
    
    # 返回标准API Gateway响应格式
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'  # 允许跨域请求
        },
        'body': json.dumps(result)
    }
```

## Lambda函数使用说明

### 输入格式

Lambda函数接受以下JSON格式的输入：

```json
{
  "Gender": 1,
  "Married": 1,
  "Dependents": 2,
  "Education": 1,
  "Self_Employed": 0,
  "ApplicantIncome": 5000,
  "CoapplicantIncome": 1000.0,
  "LoanAmount": 150.0,
  "Loan_Amount_Term": 360.0,
  "Credit_History": 1.0,
  "Property_Area": 2
}
```

### 输出格式

成功时返回的输出：

```json
{
  "prediction": 1,
  "message": "Loan Approved"
}
```

或

```json
{
  "prediction": 0,
  "message": "Loan Rejected"
}
```

## 测试Lambda函数

您可以使用AWS控制台或AWS CLI测试Lambda函数：

```bash
aws lambda invoke --function-name LoanPredictionFunction --cli-binary-format raw-in-base64-out --payload '{"Gender": 1, "Married": 1, "Dependents": 2, "Education": 1, "Self_Employed": 0, "ApplicantIncome": 5000, "CoapplicantIncome": 1000.0, "LoanAmount": 150.0, "Loan_Amount_Term": 360.0, "Credit_History": 1.0, "Property_Area": 2}' response.json
cat response.json
```

## 注意事项

1. **冷启动性能**：首次调用Lambda函数时，会有一个冷启动时间，用于加载模型和初始化环境。使用容器镜像可能会有稍长的冷启动时间。
2. **内存和超时设置**：根据您的模型大小和预测复杂度，可能需要调整Lambda函数的内存和超时设置。对于大型模型，建议增加内存配置。
3. **依赖管理**：使用Docker容器可以更好地管理依赖，确保所有库都正确安装和配置。
4. **错误处理**：Lambda函数包含了详细的错误处理和日志记录，便于调试和监控。
5. **安全最佳实践**：在生产环境中，建议使用AWS Secrets Manager或Parameter Store来管理敏感信息，并实施适当的访问控制。
6. **镜像大小**：尽量优化Docker镜像大小，移除不必要的文件和依赖，使用多阶段构建。
7. **IAM权限**：确保Lambda执行角色具有适当的权限，特别是对ECR的访问权限。
8. **容器限制**：Lambda容器镜像最大可以是10GB，比ZIP部署包的250MB限制大得多，适合部署大型模型。

## 优化建议

1. **模型优化**：考虑使用模型量化或小型化技术，减少模型大小和加载时间。
2. **Docker优化**：使用多阶段构建、精简基础镜像、移除调试工具等方式减小镜像体积。
3. **缓存策略**：利用Lambda的执行环境重用特性，优化性能。
4. **监控和日志**：设置CloudWatch告警和日志监控，及时发现和解决问题。
5. **ECR生命周期策略**：配置ECR仓库的生命周期策略，自动清理旧版本镜像。
6. **Lambda预置并发**：对于需要低延迟响应的场景，考虑配置Lambda预置并发。

## 更新Lambda函数（代码或模型变更时）

当您需要更新代码或模型时，可以按照以下步骤操作：

1. **更新代码和模型文件**
2. **重新构建Docker镜像**：
   ```bash
   docker build -t loan-prediction-lambda .
   ```
3. **重新标记并推送镜像到ECR**：
   ```bash
   docker tag loan-prediction-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest
   docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest
   ```
4. **更新Lambda函数**：
   ```bash
   aws lambda update-function-code \
       --function-name LoanPredictionFunction \
       --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:latest
   ```

## 清理AWS资源

在测试或演示完成后，建议清理AWS资源以避免不必要的费用。以下是清理步骤：

### 1. 删除API Gateway

```bash
# 设置变量（使用之前的值）
API_ID="your-api-id"

# 删除API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID
```

### 2. 删除Lambda函数

```bash
# 删除Lambda函数
aws lambda delete-function --function-name LoanPredictionFunction
```

### 3. 删除ECR仓库（先删除镜像）

```bash
# 设置变量（使用之前的值）
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # 替换为您的区域
ECR_REPOSITORY_NAME="loan-prediction-lambda"

# 获取并删除所有镜像
IMAGE_DIGESTS=$(aws ecr list-images --repository-name $ECR_REPOSITORY_NAME --query 'imageIds[*].imageDigest' --output json)

# 检查是否有镜像需要删除
if [ "$IMAGE_DIGESTS" != "[]" ]; then
    # 解析JSON数组并删除每个镜像
    echo $IMAGE_DIGESTS | jq -c '.[]' | while read -r digest; do
        digest=$(echo $digest | tr -d '"')
        aws ecr batch-delete-image \
            --repository-name $ECR_REPOSITORY_NAME \
            --image-ids imageDigest=$digest
    done
fi

# 删除ECR仓库
aws ecr delete-repository --repository-name $ECR_REPOSITORY_NAME --force
```

### 4. 删除IAM Role（先detach policy）

```bash
# 先detach policy
aws iam detach-role-policy \
    --role-name lambda-exec-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 删除IAM role
aws iam delete-role --role-name lambda-exec-role
```

### 5. 验证清理是否完成

```bash
# 检查Lambda函数是否已删除
aws lambda get-function --function-name LoanPredictionFunction 2>/dev/null || echo "Lambda函数已删除或不存在"

# 检查ECR仓库是否已删除
aws ecr describe-repositories --repository-names $ECR_REPOSITORY_NAME 2>/dev/null || echo "ECR仓库已删除或不存在"

# 检查IAM role是否已删除
aws iam get-role --role-name lambda-exec-role 2>/dev/null || echo "IAM role已删除或不存在"
```

**注意事项**：
- 请确保在删除资源前备份必要的数据
- 删除操作不可逆，请谨慎执行
- 根据您的AWS权限，某些操作可能需要管理员权限
- 删除资源后，相关的计费将停止，但可能会在下次账单中出现部分费用（按小时或按天计费的服务）