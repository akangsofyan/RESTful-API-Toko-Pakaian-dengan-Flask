from flask import Flask
from flask_uploads import configure_uploads, patch_request_class
from image_resource import ImageUpload
from image_helper import IMAGE_SET


def create_app(config_filename):
    app = Flask(__name__)
    app.config.from_object(config_filename)
    patch_request_class(app, 10 * 1024 * 2014)  # limit maximum size upload 10MB
    configure_uploads(app, IMAGE_SET)

    from models import db
    db.init_app(app)

    from views import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
