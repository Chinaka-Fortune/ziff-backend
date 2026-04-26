import os
from app import create_app
import app.models # Enable Alembic to detect models

config_name = os.environ.get('FLASK_ENV') or 'default'
app = create_app(config_name)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
