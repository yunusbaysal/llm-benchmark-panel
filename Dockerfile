FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY tasks ./tasks
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

# Default: regenerate the offline demo run + dashboard on container start.
CMD ["python", "scripts/regenerate_demo.py"]
