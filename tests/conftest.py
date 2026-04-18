import os

# Ryuk (testcontainers cleanup daemon) requires pulling an image from Docker Hub.
# Disable it — the context manager handles container cleanup correctly without it.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
