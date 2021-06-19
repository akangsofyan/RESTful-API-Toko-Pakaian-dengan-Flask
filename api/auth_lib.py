from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource

auth = HTTPBasicAuth()


class AuthRequiredResource(Resource):
    method_decorators = [auth.login_required]
