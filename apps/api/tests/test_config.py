"""Verifies UPLOAD_DIR (app/config.py) supports an environment variable
override, mirroring the existing KNOWLEDGE_DIR pattern — this is what lets a
host with ephemeral local disk (e.g. Render, without a persistent disk
attached to the default path) point uploaded-PDF storage at a mounted
persistent disk instead, purely via configuration.

UPLOAD_DIR is a module-level constant computed once at import time (not a
pydantic Settings field), so testing the override requires reloading
app.config under a controlled environment rather than just instantiating
Settings() again."""
import importlib
import os
import tempfile


def test_upload_dir_defaults_to_local_data_folder_when_unset():
    import app.config as config_module

    original = os.environ.pop("UPLOAD_DIR", None)
    try:
        importlib.reload(config_module)
        assert config_module.UPLOAD_DIR == config_module.DATA_DIR / "uploads"
        assert config_module.UPLOAD_DIR.exists()
    finally:
        if original is not None:
            os.environ["UPLOAD_DIR"] = original
        importlib.reload(config_module)


def test_upload_dir_can_be_overridden_via_environment_variable():
    import app.config as config_module

    original = os.environ.get("UPLOAD_DIR")
    override_dir = os.path.join(tempfile.mkdtemp(), "render_persistent_disk_uploads")
    os.environ["UPLOAD_DIR"] = override_dir
    try:
        importlib.reload(config_module)
        assert str(config_module.UPLOAD_DIR) == override_dir
        # config.py creates the directory on load (mkdir(parents=True,
        # exist_ok=True)) — matters in production where the mount exists
        # but a subdirectory under it might not yet.
        assert config_module.UPLOAD_DIR.exists()
    finally:
        if original is None:
            os.environ.pop("UPLOAD_DIR", None)
        else:
            os.environ["UPLOAD_DIR"] = original
        importlib.reload(config_module)


def test_upload_dir_override_does_not_affect_knowledge_dir_or_database_url():
    """The override must be scoped to UPLOAD_DIR only — this change must not
    accidentally couple upload storage to the knowledge base path or the
    database configuration, both of which are explicitly out of scope here."""
    import app.config as config_module

    original = os.environ.get("UPLOAD_DIR")
    original_db_url = config_module.settings.database_url
    original_knowledge_dir = config_module.KNOWLEDGE_DIR
    os.environ["UPLOAD_DIR"] = os.path.join(tempfile.mkdtemp(), "isolated_override")
    try:
        importlib.reload(config_module)
        assert config_module.KNOWLEDGE_DIR == original_knowledge_dir
        assert config_module.settings.database_url == original_db_url
    finally:
        if original is None:
            os.environ.pop("UPLOAD_DIR", None)
        else:
            os.environ["UPLOAD_DIR"] = original
        importlib.reload(config_module)
