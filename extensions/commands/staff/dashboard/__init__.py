# extensions/commands/staff/dashboard/__init__.py
from . import dashboard

# Import handlers with error handling to debug registration issues
try:
    from . import handlers
    print("[Staff Dashboard] Handlers imported successfully")
except Exception as e:
    print(f"[Staff Dashboard] ERROR importing handlers: {e}")
    import traceback
    traceback.print_exc()
