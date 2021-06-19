import datetime

from flask import Blueprint, request, jsonify, make_response, url_for, render_template
from flask_restful import Api, Resource
from models import db, Category, CategorySchema, Product, ProductSchema
from sqlalchemy.exc import SQLAlchemyError
import status
from helpers import PaginationHelper
from flask import g
from models import User, UserSchema
from email_utils import send_email
from token_mail import generate_confirmation_token, confirm_token

from image_resource import Avatar, AvatarUpload, Image, ImageUpload

from auth_lib import auth, AuthRequiredResource


@auth.verify_password
def verify_user_password(name, password):
    user = User.query.filter_by(name=name).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True


api_bp = Blueprint('api', __name__)
category_schema = CategorySchema()
product_schema = ProductSchema()
user_schema = UserSchema()
api = Api(api_bp)


class UserResource(AuthRequiredResource):
    def get(self, id):
        user = User.query.get_or_404(id)
        result = user_schema.dump(user).data
        return result


class ConfirmTokenResources(Resource):
    def get(self, token):
        try:
            email = confirm_token(token)
        except:
            response = {'token': 'The confirmation link is invalid or has expired.'}
            return response, status.HTTP_400_BAD_REQUEST
        user = User.query.filter_by(email=email).first_or_404()
        if user.confirmed:
            response = {'user': 'Account already confirmed. Please login.'}
            return response, status.HTTP_200_OK
        else:
            user.confirmed = True
            user.confirmed_on = datetime.datetime.now()
            db.session.add(user)
            db.session.commit()
            response = {'user': 'You have confirmed your account. Thanks!'}
            return response, status.HTTP_201_CREATED


class UserListResource(Resource):
    @auth.login_required
    def get(self):
        pagination_helper = PaginationHelper(
            request,
            query=User.query,
            resource_for_url='api.userlistresource',
            key_name='results',
            schema=user_schema)
        result = pagination_helper.paginate_query()
        return result

    def post(self):
        request_dict = request.get_json()
        if not request_dict:
            response = {'user': 'No input data provided'}
            return response, status.HTTP_400_BAD_REQUEST
        errors = user_schema.validate(request_dict)
        if errors:
            return errors, status.HTTP_400_BAD_REQUEST
        name = request_dict['name']
        email = request_dict['email']
        existing_user = User.query.filter_by(name=name).first()
        if existing_user is not None:
            response = {'user': 'An user with the same name already exists'}
            return response, status.HTTP_400_BAD_REQUEST
        try:
            user = User(name=name, email=email)
            error_message, password_ok = \
                user.check_password_strength_and_hash_if_ok(request_dict['password'])
            if password_ok:
                user.add(user)
                query = User.query.get(user.id)
                result = user_schema.dump(query).data
                token = generate_confirmation_token(user.email)
                confirm_url = url_for('api.confirmtokenresources', token=token, _external=True)
                html = render_template('user/activate.html', confirm_url=confirm_url)
                subject = "Please confirm your email"
                # send_email(user.email, subject, html)

                print(f"Token: registration: {token}")

                return result, status.HTTP_201_CREATED
            else:
                return {"error": error_message}, status.HTTP_400_BAD_REQUEST
        except SQLAlchemyError as e:
            db.session.rollback()
            resp = {"error": str(e)}
            return resp, status.HTTP_400_BAD_REQUEST


class ProductResource(AuthRequiredResource):
    def get(self, id):
        product = Product.query.get_or_404(id)
        result = product_schema.dump(product).data
        return result

    def patch(self, id):
        product = Product.query.get_or_404(id)
        product_dict = request.get_json(force=True)
        if 'product' in product_dict:
            product.product = product_dict['product']
            if Product.is_unique(id=id, product=product.product):
                Product.product = product.product
            else:
                response = {'error': 'A message with the same name already exists'}
                return response, status.HTTP_400_BAD_REQUEST
        if 'price' in product_dict:
            product.price = product_dict['price']
        if 'size' in product_dict:
            product.size = product_dict['size']
        if 'quantity' in product_dict:
            product.quantity = product_dict['quantity']
        if 'printed_times' in product_dict:
            product.printed_times = product_dict['printed_times']
        if 'printed_once' in product_dict:
            product.printed_once = product_dict['printed_once']
        dumped_product, dump_errors = product_schema.dump(product)
        if dump_errors:
            return dump_errors, status.HTTP_400_BAD_REQUEST
        validate_errors = product_schema.validate(dumped_product)
        if validate_errors:
            return validate_errors, status.HTTP_400_BAD_REQUEST
        try:
            product.update()
            return self.get(id)
        except SQLAlchemyError as e:
                db.session.rollback()
                resp = {"error": str(e)}
                return resp, status.HTTP_400_BAD_REQUEST

    def delete(self, id):
        product = Product.query.get_or_404(id)
        try:
            delete = product.delete(product)
            response = make_response()
            return response, status.HTTP_204_NO_CONTENT
        except SQLAlchemyError as e:
                db.session.rollback()
                resp = jsonify({"error": str(e)})
                return resp, status.HTTP_401_UNAUTHORIZED


class ProductListResource(AuthRequiredResource):
    def get(self):
        pagination_helper = PaginationHelper(
            request,
            query=Product.query,
            resource_for_url='api.productlistresource',
            key_name='results',
            schema=product_schema)
        result = pagination_helper.paginate_query()
        return result

    def post(self):
        request_dict = request.get_json()
        if not request_dict:
            response = {'message': 'No input data provided'}
            return response, status.HTTP_400_BAD_REQUEST
        errors = product_schema.validate(request_dict)
        if errors:
            return errors, status.HTTP_400_BAD_REQUEST
        product_product = request_dict['product']
        if not Product.is_unique(id=0, product=product_product):
            response = {'error': 'A product with the same name already exists'}
            return response, status.HTTP_400_BAD_REQUEST
        try:
            category_name = request_dict['category']['name']
            category = Category.query.filter_by(name=category_name).first()
            if category is None:
                # Create a new Category
                category = Category(name=category_name)
                db.session.add(category)
            # Now that we are sure we have a category
            # create a new Message
            product = Product(
                product=product_product,
                price=request_dict['price'],
                size=request_dict['size'],
                quantity=request_dict['quantity'],
                category=category)
            product.add(product)
            query = Product.query.get(product.id)
            result = product_schema.dump(query).data
            return result, status.HTTP_201_CREATED
        except SQLAlchemyError as e:
            db.session.rollback()
            resp = {"error": str(e)}
            return resp, status.HTTP_400_BAD_REQUEST


class CategoryResource(AuthRequiredResource):
    def get(self, id):
        category = Category.query.get_or_404(id)
        result = category_schema.dump(category).data
        return result

    def patch(self, id):
        category = Category.query.get_or_404(id)
        category_dict = request.get_json()
        if not category_dict:
            resp = {'message': 'No input data provided'}
            return resp, status.HTTP_400_BAD_REQUEST
        errors = category_schema.validate(category_dict)
        if errors:
            return errors, status.HTTP_400_BAD_REQUEST
        try:
            if 'name' in category_dict:
                category_name = category_dict['name']
                if Category.is_unique(id=id, name=category_name):
                    category.name = category_name
                else:
                    response = {'error': 'A category with the same name already exists'}
                    return response, status.HTTP_400_BAD_REQUEST
            category.update()
            return self.get(id)
        except SQLAlchemyError as e:
                db.session.rollback()
                resp = {"error": str(e)}
                return resp, status.HTTP_400_BAD_REQUEST

    def delete(self, id):
        category = Category.query.get_or_404(id)
        try:
            category.delete(category)
            response = make_response()
            return response, status.HTTP_204_NO_CONTENT
        except SQLAlchemyError as e:
                db.session.rollback()
                resp = jsonify({"error": str(e)})
                return resp, status.HTTP_401_UNAUTHORIZED


class CategoryListResource(AuthRequiredResource):
    def get(self):
        categories = Category.query.all()
        results = category_schema.dump(categories, many=True).data
        return results

    def post(self):
        request_dict = request.get_json()
        if not request_dict:
            resp = {'message': 'No input data provided'}
            return resp, status.HTTP_400_BAD_REQUEST
        errors = category_schema.validate(request_dict)
        if errors:
            return errors, status.HTTP_400_BAD_REQUEST
        category_name = request_dict['name']
        if not Category.is_unique(id=0, name=category_name):
            response = {'error': 'A category with the same name already exists'}
            return response, status.HTTP_400_BAD_REQUEST
        try:
            category = Category(category_name)
            category.add(category)
            query = Category.query.get(category.id)
            result = category_schema.dump(query).data
            return result, status.HTTP_201_CREATED
        except SQLAlchemyError as e:
            db.session.rollback()
            resp = {"error": str(e)}
            return resp, status.HTTP_400_BAD_REQUEST


api.add_resource(CategoryListResource, '/categories/')
api.add_resource(CategoryResource, '/categories/<int:id>')
api.add_resource(ProductListResource, '/products/')
api.add_resource(ProductResource, '/products/<int:id>')
api.add_resource(UserListResource, '/users/')
api.add_resource(UserResource, '/users/<int:id>')
api.add_resource(ConfirmTokenResources, '/users/confirm/<string:token>')

api.add_resource(ImageUpload, "/upload/image")
api.add_resource(Image, "/image/<string:filename>")
api.add_resource(AvatarUpload, "/upload/avatar")
api.add_resource(Avatar, "/avatar/<int:user_id>")
