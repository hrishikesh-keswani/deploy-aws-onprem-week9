FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY risk_agent ./risk_agent
COPY fixtures ./fixtures

ENV LLM_PROVIDER=bedrock
ENV BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
ENV AWS_REGION=us-east-1
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "risk_agent"]
