FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Install system dependencies and Poetry in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -c "import urllib.request; urllib.request.urlretrieve('https://install.python-poetry.org', 'poetry-installer.py')" \
    && python3 poetry-installer.py \
    && rm poetry-installer.py

# Set working directory
WORKDIR $PYSETUP_PATH

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./

# Install production dependencies
RUN poetry install --no-root --no-dev

# Copy the entrypoint script first and make it executable
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Copy application code
COPY . .

# Clean up
RUN rm -rf ~/.cache/pypoetry

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
