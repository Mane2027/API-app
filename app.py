import os
from datetime import timedelta, datetime

import bcrypt
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt,
)
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Configuración de la aplicación
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
    hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 8))
)

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)


# ---------------------------------------------------------------------------
# Excepción propia para errores de negocio con código HTTP asociado
# ---------------------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@app.errorhandler(ApiError)
def handle_api_error(error: ApiError):
    return jsonify({'message': error.message}), error.status_code


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({'message': 'Recurso no encontrado'}), 404


@app.errorhandler(500)
def handle_internal_error(error):
    return jsonify({'message': 'Error interno del servidor'}), 500


# ---------------------------------------------------------------------------
# Modelos (clases ORM)
# ---------------------------------------------------------------------------
class User(db.Model):
    """Representa la tabla 'users'. Encapsula el hash/verificación de contraseña."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='vendedor')  # 'admin' | 'vendedor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, plain_password: str) -> None:
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed.decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Product(db.Model):
    """
    Representa la tabla 'products': el inventario de la tienda de belleza
    (maquillaje, cuidado facial, cuidado capilar, cuidado corporal,
    perfumería, uñas, accesorios, etc.)
    """

    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False, unique=True)  # código interno del producto
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    brand = db.Column(db.String(100), nullable=False)  # marca: Maybelline, L'Oréal, Nivea, etc.
    category = db.Column(db.String(30), nullable=False, default='otro')
    # categorías esperadas: maquillaje, cuidado_facial, cuidado_capilar,
    # cuidado_corporal, perfumeria, unas, accesorios, otro
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=True)  # costo de adquisición (para margen)
    stock = db.Column(db.Integer, nullable=False, default=0)
    min_stock = db.Column(db.Integer, nullable=False, default=5)  # umbral de bajo stock
    expiration_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # baja lógica
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_low_stock(self) -> bool:
        return self.stock <= self.min_stock

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'brand': self.brand,
            'category': self.category,
            'price': self.price,
            'cost': self.cost,
            'stock': self.stock,
            'min_stock': self.min_stock,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'is_active': self.is_active,
            'is_low_stock': self.is_low_stock(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Servicios (lógica de negocio, en clases, separada de las rutas)
# ---------------------------------------------------------------------------
class AuthService:
    def register(self, name, email, password, role='vendedor') -> dict:
        if User.query.filter_by(email=email).first():
            raise ApiError('El correo ya está registrado', 409)

        user = User(name=name, email=email, role=role or 'vendedor')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.to_dict()

    def login(self, email, password) -> dict:
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            raise ApiError('Credenciales inválidas', 401)

        token = create_access_token(
            identity=str(user.id),
            additional_claims={'email': user.email, 'role': user.role},
        )
        return {'token': token, 'user': user.to_dict()}


class UserService:
    def get_all(self) -> list:
        return [u.to_dict() for u in User.query.all()]

    def get_by_id(self, user_id: int) -> dict:
        user = User.query.get(user_id)
        if not user:
            raise ApiError('Usuario no encontrado', 404)
        return user.to_dict()

    def create(self, name, email, password, role='vendedor') -> dict:
        if User.query.filter_by(email=email).first():
            raise ApiError('El correo ya está registrado', 409)

        user = User(name=name, email=email, role=role or 'vendedor')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.to_dict()

    def update(self, user_id: int, data: dict) -> dict:
        user = User.query.get(user_id)
        if not user:
            raise ApiError('Usuario no encontrado', 404)

        if data.get('name'):
            user.name = data['name']
        if data.get('email'):
            user.email = data['email']
        if data.get('role'):
            user.role = data['role']
        if data.get('password'):
            user.set_password(data['password'])

        db.session.commit()
        return user.to_dict()

    def delete(self, user_id: int) -> dict:
        user = User.query.get(user_id)
        if not user:
            raise ApiError('Usuario no encontrado', 404)
        db.session.delete(user)
        db.session.commit()
        return {'message': 'Usuario eliminado correctamente'}


class ProductService:
    CATEGORIES = (
        'maquillaje', 'cuidado_facial', 'cuidado_capilar', 'cuidado_corporal',
        'perfumeria', 'unas', 'accesorios', 'otro',
    )

    def get_all(self, filters: dict = None) -> list:
        filters = filters or {}
        query = Product.query

        if filters.get('category'):
            query = query.filter_by(category=filters['category'])
        if filters.get('brand'):
            query = query.filter_by(brand=filters['brand'])
        if filters.get('search'):
            query = query.filter(Product.name.ilike(f"%{filters['search']}%"))

        products = query.order_by(Product.name.asc()).all()

        if filters.get('lowStock') == 'true':
            products = [p for p in products if p.is_low_stock()]

        return [p.to_dict() for p in products]

    def get_by_id(self, product_id: int) -> dict:
        product = Product.query.get(product_id)
        if not product:
            raise ApiError('Producto no encontrado', 404)
        return product.to_dict()

    def _parse_expiration(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ApiError('expiration_date debe tener formato YYYY-MM-DD', 400)

    def create(self, data: dict) -> dict:
        if not data.get('sku') or not data.get('name') or not data.get('brand') or data.get('price') is None:
            raise ApiError('sku, name, brand y price son obligatorios', 400)

        if Product.query.filter_by(sku=data['sku']).first():
            raise ApiError('Ya existe un producto con ese SKU', 409)

        product = Product(
            sku=data['sku'],
            name=data['name'],
            description=data.get('description'),
            brand=data['brand'],
            category=data.get('category', 'otro'),
            price=data['price'],
            cost=data.get('cost'),
            stock=data.get('stock', 0),
            min_stock=data.get('min_stock', 5),
            expiration_date=self._parse_expiration(data.get('expiration_date')),
            is_active=data.get('is_active', True),
        )
        db.session.add(product)
        db.session.commit()
        return product.to_dict()

    def update(self, product_id: int, data: dict) -> dict:
        product = Product.query.get(product_id)
        if not product:
            raise ApiError('Producto no encontrado', 404)

        if 'sku' in data and data['sku'] and data['sku'] != product.sku:
            if Product.query.filter_by(sku=data['sku']).first():
                raise ApiError('Ya existe un producto con ese SKU', 409)
            product.sku = data['sku']

        for field in ('name', 'description', 'brand', 'category', 'price', 'cost', 'stock', 'min_stock', 'is_active'):
            if data.get(field) is not None:
                setattr(product, field, data[field])

        if 'expiration_date' in data:
            product.expiration_date = self._parse_expiration(data.get('expiration_date'))

        db.session.commit()
        return product.to_dict()

    def delete(self, product_id: int) -> dict:
        product = Product.query.get(product_id)
        if not product:
            raise ApiError('Producto no encontrado', 404)
        db.session.delete(product)
        db.session.commit()
        return {'message': 'Producto eliminado correctamente'}


auth_service = AuthService()
user_service = UserService()
product_service = ProductService()


# ---------------------------------------------------------------------------
# Decorador de autorización por rol (uso opcional junto a @jwt_required())
# ---------------------------------------------------------------------------
def role_required(*roles):
    from functools import wraps

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') not in roles:
                return jsonify({'message': 'No tienes permisos para esta acción'}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Rutas — Autenticación
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return jsonify({'message': 'API del sistema de inventario de la tienda de belleza funcionando correctamente'})


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role')

    if not name or not email or not password:
        return jsonify({'message': 'name, email y password son obligatorios'}), 400

    user = auth_service.register(name, email, password, role)
    return jsonify(user), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email, password = data.get('email'), data.get('password')

    if not email or not password:
        return jsonify({'message': 'email y password son obligatorios'}), 400

    result = auth_service.login(email, password)
    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Rutas — CRUD de Usuarios (protegidas con JWT)
# ---------------------------------------------------------------------------
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    return jsonify(user_service.get_all()), 200


@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    return jsonify(user_service.get_by_id(user_id)), 200


@app.route('/api/users', methods=['POST'])
@jwt_required()
def create_user():
    data = request.get_json(silent=True) or {}
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role')

    if not name or not email or not password:
        return jsonify({'message': 'name, email y password son obligatorios'}), 400

    return jsonify(user_service.create(name, email, password, role)), 201


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    return jsonify(user_service.update(user_id, data)), 200


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    return jsonify(user_service.delete(user_id)), 200


# ---------------------------------------------------------------------------
# Rutas — CRUD de Productos/Servicios (protegidas con JWT)
# ---------------------------------------------------------------------------
@app.route('/api/products', methods=['GET'])
@jwt_required()
def get_products():
    # Filtros opcionales por query string:
    # ?category=maquillaje&brand=Nivea&lowStock=true&search=labial
    return jsonify(product_service.get_all(request.args)), 200


@app.route('/api/products/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    return jsonify(product_service.get_by_id(product_id)), 200


@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    data = request.get_json(silent=True) or {}
    return jsonify(product_service.create(data)), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    return jsonify(product_service.update(product_id, data)), 200


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    return jsonify(product_service.delete(product_id)), 200


# ---------------------------------------------------------------------------
# Creación de tablas e inicio de la aplicación
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
