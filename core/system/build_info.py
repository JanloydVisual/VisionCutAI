from datetime import datetime

class BuildInfo:
    """
    Contains application version and build metadata for Beta deployment.
    """
    VERSION = "0.9.0-beta1"
    BUILD_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ENABLED_FEATURES = [
        "multi_object_tracking",
        "cache_optimization",
        "export_composite",
        "beta_telemetry"
    ]
    MODEL_VERSIONS = {
        "mobile_sam": "v1.0.3",
        "tracking_engine": "v2.1.0"
    }
