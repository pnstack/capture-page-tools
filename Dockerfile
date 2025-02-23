# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm

# Install Chrome and dependencies
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# set display port to avoid crash
ENV DISPLAY=:99

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run setup.py
RUN python setup.py

# Create cache directories and set permissions
RUN mkdir -p /.cache/selenium && \
    mkdir -p /tmp/screenshots && \
    chown -R appuser:appuser /.cache/selenium && \
    chown -R appuser:appuser /tmp/screenshots && \
    chmod 755 /.cache/selenium && \
    chmod 755 /tmp/screenshots

# Set temporary directory environment variable
ENV TMPDIR=/tmp/screenshots

# Set user
USER appuser

EXPOSE 7860
# Run the FastAPI application by default
CMD ["python", "main.py"]
