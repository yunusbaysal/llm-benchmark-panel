FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cached separately from source code)
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir ".[dev]"

# Copy source after dependencies to maximise cache reuse
COPY src ./src
COPY tasks ./tasks
COPY data ./data
COPY scripts ./scripts

# Install the package itself (non-editable, production-appropriate)
RUN pip install --no-cache-dir --no-deps .

# Run as a non-root user
RUN adduser --disabled-password --gecos "" benchuser
USER benchuser

# Default: regenerate the offline demo run + dashboard on container start.
CMD ["python", "scripts/regenerate_demo.py"]
