# Disable telemetry globally to prevent network timeouts during testing
import os
os.environ["SOL_TELEMETRY_ENABLED"] = "false"
