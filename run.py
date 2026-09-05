import os
import sys
from app import create_app

# Set UTF-8 encoding for Windows console if needed
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    print(f">> BlockCert backend starting on http://127.0.0.1:{port}")
    print(f">> Local access URL: http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=debug)
