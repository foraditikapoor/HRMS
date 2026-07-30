import os
import threading
import time
import webbrowser

from app import app


def _open_browser():
    # small delay to allow the server to start
    time.sleep(1.0)
    url = os.environ.get('HRMS_URL', 'http://127.0.0.1:5000')
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001, S110  # Ignore browser opening failures during launch
        pass


if __name__ == '__main__':
    threading.Thread(target=_open_browser, daemon=True).start()
    # run without debug for packaged usage
    app.run(host='127.0.0.1', port=5000, debug=False)

