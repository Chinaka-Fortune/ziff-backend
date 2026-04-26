import os
import sys

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Vercel looks for 'app' as the export
app = create_app(os.environ.get('FLASK_ENV') or 'default')

# This is required for Vercel to handle the app correctly
if __name__ == "__main__":
    app.run()
