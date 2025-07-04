FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install curl for downloading UV, then clean up after installation
RUN apt-get update && \
    apt-get install -y build-essential freetds-dev freetds-bin unixodbc-dev libssl-dev libkrb5-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install dependencies with UV
COPY pyproject.toml ./

# Create virtual environment
RUN uv venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# TEMP FIX FOR CYTHON 3.1.0
RUN uv pip install "packaging>=24" "setuptools>=54.0" "setuptools_scm[toml]>=8.0" "wheel>=0.36.2" "Cython==3.0.10" "tomli"
RUN uv pip install --pre --no-binary :all: pymssql --no-cache --no-build-isolation

RUN uv pip install -e .

# Copy your server script, business_request module, and environment files
COPY server.py ./
COPY business_request/ ./business_request/

EXPOSE 8000

CMD ["python", "server.py"]