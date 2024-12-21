from app.shared.config import init_settings

# Initialize settings first
settings = init_settings()

# Then import other modules that need settings

__version__ = settings.VERSION
