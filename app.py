from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import jwt
import datetime
import pika
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = 'thisisthesecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

def send_message_to_queue(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', pika.PlainCredentials('user', 'password')))
    channel = connection.channel()
    channel.queue_declare(queue='book_queue')
    channel.basic_publish(exchange='', routing_key='book_queue', body=message)
    connection.close()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50))
    title = db.Column(db.String(100))

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # if 'token' in request.args:
        #     token = request.args.get('token')

        token = None

        if 'x-access-tokens' in request.headers:  
            token = request.headers['x-access-tokens'] 

        if not token:
            return jsonify({'message': 'Token is missing'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

with app.app_context():
     db.create_all()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(public_id=str(uuid.uuid4()), username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully!'})

@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id': user.public_id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})

    return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route('/protected_authors', methods=['POST'])
@token_required
def add_book(current_user):
    data = request.get_json()

    new_book = Book(author=data['author'], title=data['title'])
    db.session.add(new_book)
    db.session.commit()

    message = f"New book added by {current_user.username}: {data['title']} by {data['author']}"
    send_message_to_queue(message)

    return jsonify({'message': 'Book added successfully!'})

@app.route('/all_books', methods=['GET'])
@token_required
def get_all_books(current_user):
    books = Book.query.all()

    output = []
    for book in books:
        book_data = {'author': book.author, 'title': book.title}
        output.append(book_data)

    return jsonify({'books': output})

if __name__ == '__main__':
    app.run(debug=True)