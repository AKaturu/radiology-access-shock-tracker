FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN radshock demo --output-dir outputs/demo

EXPOSE 8501
CMD ["streamlit", "run", "src/radshock/app.py", "--server.address=0.0.0.0"]
