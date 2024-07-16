from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_pymongo import PyMongo
from mongoengine import connect
import requests
from bson.objectid import ObjectId
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import datetime
import json
import math
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from mongoengine.queryset.visitor import Q
from functools import wraps
from model.model import Rune
from flask_limiter import Limiter
from flask_restx import Api, Resource, fields
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_socketio import SocketIO, emit

load_dotenv()


app = Flask(__name__)
api = Api(app, version='1.0', title='Rune API', description='APIs to manage runes', doc='/docs')
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure Flask-Caching with Redis
app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_HOST'] = 'localhost'
app.config['CACHE_REDIS_PORT'] = 6380
app.config['CACHE_REDIS_DB'] = 0
app.config['CACHE_REDIS_URL'] = os.getenv("REDIS_URL", "redis://localhost:6380/0")
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Cache timeout in seconds

cache = Cache(app)

# Define a function to create and configure the Limiter object
def create_limiter(app):
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100 per day", "10 per hour"]
    )
    limiter.init_app(app)
    return limiter

# Use the factory function to create and configure the Limiter object
limiter = create_limiter(app)
cors = CORS(app, origins=['https://mint-iz3y.onrender.com/en/mint-runes', 'https://mint-iz3y.onrender.com/', 'https://mint-iz3y.onrender.com', 'mint-iz3y.onrender.com/','localhost:3000','https://localhost:3000', 'https://development-3mci.onrender.com/' , 'http://localhost:3000', 'https://rune-frontend.onrender.com', 'https://rune-frontend-2.onrender.com', 'https://development.runepro.com', 'https://development.onrender.com', 'https://rune-dashboard.onrender.com', 'http://localhost:5500/', 'http://localhost:8888', 'https://runepro-test.vercel.app', 'https://runepro.com', 'https://www.runepro.com', 'https://testnet.runepro.com',  'https://rune-frontend-1.onrender.com', 'https://development-3mci.onrender.com/'])

URL = "https://testnet-backend-ivoa.onrender.com"

# connect('test_database', host='mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net')



# uri = os.getenv("MONGO_URI")
# db = os.getenv("DB")
# app.config["MONGO_URI"] = "mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database"
# # client = MongoClient('mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database', )
# Set up the MongoDB connection URI with SSL and the CA certificate file
# cafile = certifi.where()
# mongo_uri = f"mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database?ssl=true&tlsCAFile={cafile}"


# Set the MONGO_URI configuration for Flask-PyMongo
# app.config["MONGO_URI"] = mongo_uri

# Initialize PyMongo with the Flask app
# pymongo = PyMongo(app)

# Define a dictionary to store API keys and their associated users or clients

# Define a dictionary to store API keys and their associated users or clients
api_keys = {
    'api_key': 'rune@python'
}


# Decorator function to require API key authentication
def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if api_key != api_keys['api_key']:
            return jsonify({'error': 'Unauthorized'}), 401
        return func(*args, **kwargs)  # Call the original function without passing the user argument
    return wrapper

error_missingInfo = "RP101"
error_missingInscription = "RP102"
error_offer_already_exist ="RP106"
error_offer_not_exist= "RP108"
error_offer_is_invalid="RP109"
error_invalid = "RP103"
error_wallet = "RP104"
error_misc = "RP105"
error_not_enough_balance = "RP107"
error_missingSetup = "RP110"

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_URI"),
    integrations=[FlaskIntegration()],
    release=os.environ.get("VERSION"),
    enable_tracing=True,
    
)
def check_db_connection():
    try:
        # Connect to MongoDB using MongoEngine
        connect(
            db="test_database",  # replace with your database name
            host="mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database",
            tlsCAFile=certifi.where()
        )
        print("Connected to DB. Server status: MongoDB")
    except Exception as e:
        print("Failed to connect to DB:", str(e))

check_db_connection()

# def check_db_connection():
#     try:
#         client = MongoClient("mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database",tlsCAFile=certifi.where())
#   # replace with your MongoDB URI
#         db = client.test  # replace 'test' with your database name
#         # The ismaster command is cheap and does not require auth.
#         server_status = db.command("serverStatus")
#         print("Connected to DB. Server status:", server_status)
#     except Exception as e:
#         print("Failed to connect to DB:", str(e))

# check_db_connection()

@app.route('/throwerror')
def throw_error(): 
    1/0  # raises an error
    return "<p>Hello, World!</p>"

@app.route('/getfeerates')
@cache.cached(timeout=300)
def GetFeeRates():
    return requests.get(URL+"/getfeerates").json()

@app.route('/')
def hello_world():
    return 'Hello, friend!'

@app.route('/runes/points', methods=['POST'])
@cache.cached(timeout=300, query_string=True)
def getPoints():
    args = request.get_json()
    addr = args['OrdinalAddress']
    points = Rune.objects(Address=addr).first()
    if points==None:
        return jsonify({'points': 0})
    return jsonify({'points': points['Points']})

# @app.route('/runes', methods=['POST'])
# def RuneIndex():
#     runes = pymongo.db.runeInfo.find({'Mintable':True},{ "_id": 0})
#     runelist = [a for a in runes]
#     runelist.reverse()
#     runes = pymongo.db.runeInfo.find({'Mintable':False},{ "_id": 0})
#     runelist2 = [a for a in runes]
#     runelist += runelist2
#     return runelist

# Define a model for the request parameters
pagination_params = api.model('Pagination', {
    'page': fields.Integer(description='Page number', example=1, default=1),
    'limit': fields.Integer(description='Number of items per page', example=10, default=10),
    'search': fields.String(description='Search query', example='example search term', default='')
})

# Define a model for the response metadata
metadata_model = api.model('Metadata', {
    'pageNumber': fields.Integer(description='Current page number'),
    'perPage': fields.Integer(description='Number of items per page'),
    'pageCount': fields.Integer(description='Number of items on the current page'),
    'totalCount': fields.Integer(description='Total number of items'),
    'numOfPages': fields.Integer(description='Total number of pages')
})


# Define rune model
rune_model = api.model('Rune', {
    '_id': fields.String(description='ID of the rune'),
    'SpacedRune': fields.String(description='Spaced Rune'),
    'RuneID': fields.String(description='Rune ID'),
    'Symbol': fields.String(description='Symbol'),
    'Created': fields.DateTime(description='Creation date'),
    'Divisibility': fields.Integer(description='Divisibility'),
    'EtchTx': fields.String(description='Etch Transaction'),
    'LimitPerMint': fields.Integer(description='Limit per Mint'),
    'MaxMintNumber': fields.Integer(description='Maximum Mint Number'),
    'Premine': fields.Integer(description='Premine'),
    'Supply': fields.Integer(description='Supply'),
    'Mintable': fields.Boolean(description='Mintable'),
})

# Define response model
response_model = api.model('Response', {
    'runes': fields.List(fields.Nested(rune_model), description='List of runes'),
    'metadata': fields.Nested(metadata_model, description='Metadata for the response')
})

@api.route('/runes')
class RuneResource(Resource):
    @api.doc(description='Get a list of runes with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(response_model)
    @limiter.limit("5 per minute")
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    def post(self):
        try:
            page = int(request.json.get('page', 1))
            limit = int(request.json.get('limit', 10))
            search_query = request.json.get('search', '')
            skip = (page - 1) * limit

            # Log the input parameters
            app.logger.debug(f"Page: {page}, Limit: {limit}, Search Query: {search_query}")

            # Construct the query
            regex_query = Q(SpacedRune__icontains=search_query) | Q(Symbol__icontains=search_query)
            app.logger.debug(f"Executing query: {regex_query}")

            runes = Rune.objects(regex_query).skip(skip).limit(limit)
            total_count = Rune.objects(regex_query).count()

            # Check if runes are found
            if not runes:
                app.logger.debug("No runes found for the given search query.")

            # Log the found runes
            app.logger.debug(f"Found runes: {[r.to_mongo().to_dict() for r in runes]}")

            # Format the runes list
            runelist = []
            for rune in runes:
                rune_dict = rune.to_mongo().to_dict()
                rune_dict['_id'] = str(rune_dict['_id'])
                runelist.append(rune_dict)

            # Prepare metadata
            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(runelist),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }
            response_data = {
                "runes": runelist,
                "metadata": metadata
            }

            # Log response data
            app.logger.debug(f"Response data: {response_data}")

            # Emit event to WebSocket clients
            socketio.emit('runes_retrieved', response_data)

            return response_data
        except Exception as e:
            app.logger.exception("Internal server error")
            sentry_sdk.capture_exception(e)
            api.abort(500, f"Internal server error: {str(e)}")

# @app.route('/rune', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def SingleRuneInfo():
#     args = request.get_json()
#     name = args['rune']
#     rune = Rune.objects(SpacedRune=name).exclude('_id').first()
#     return rune.to_json()

# @app.route('/runes/balance', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def balances():
#     args = request.get_json()
#     addr = args['OrdinalAddress']
#     return requests.post(URL+"/runes/balance", json= {'OrdinalAddress':addr}).json()

# @app.route('/runes/make-psbt', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def makeRunePsbt():
#     args = request.get_json()
#     try:
#         payaddr = args['PaymentAddress']
#         ordaddr = args['OrdinalAddress']
#         rune = args['rune']
#         amount = float(args['amount'])
#         price = float(args['price'])
#         wallet = args['wallet']
#         typ = args['type']
#     except:
#         return jsonify({'error': "Not enough info", 'code':error_missingInfo})
#     return requests.post(URL+"/runes/make-psbt", json=args).json()

# @app.route('/runes/make-listing', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def makeRuneListing():
#     args = request.get_json()
#     try:
#         payaddr = args['PaymentAddress']
#         ordaddr = args['OrdinalAddress']
#         rune = args['rune']
#         amount = float(args['amount'])
#         price = float(args['price'])
#         wallet = args['wallet']
#         typ = args['type']
#         pst = args['psbt']
#     except:
#         return jsonify({'error': "Not enough info", 'code':error_missingInfo})
#     return requests.post(URL+"/runes/make-listing", json=args).json()

# @app.route('/runes/complete-listing', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def completePsbt():
#     args = request.get_json()
#     payaddr = args['PaymentAddress']
#     ordaddr = args['OrdinalAddress']
#     wallet = args['wallet']
#     id = args['id']
#     if wallet == 'xverse':
#         pubkey = args['pubKey']
#     return requests.post(URL+"/runes/complete-listing", json=args).json()

# # @app.route('/runes/completed', methods=['POST'])
# # def completedRune():
# #     args = request.get_json()
# #     id = args.get('id')
# #     txid = args.get('txid')
# #     listing = pymongo.db.runelistings.find_one({"_id": ObjectId(id)})
# #     if (listing == None):
# #         return jsonify({'error': "That listing does not exist.", 'code':error_offer_not_exist})
# #     if (listing['valid'] != True):
# #         return jsonify({'error':"This listing is no longer valid.", 'code':error_offer_is_invalid})
# #     return requests.post(URL+"/runes/completed", json=args).json()

# @app.route('/runes/completed', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def completedRune():
#     args = request.get_json()
#     _id = args.get('id')
#     txid = args.get('txid')

#     # Query for the listing using mongoengine
#     listing = RuneListing.objects(_id=ObjectId(_id)).first()

#     # Error handling
#     if listing is None:
#         return jsonify({'error': "That listing does not exist.", 'code': error_offer_not_exist})
#     if not listing.valid:
#         return jsonify({'error': "This listing is no longer valid.", 'code': error_offer_is_invalid})

#     # Forward the request if the listing is valid
#     return requests.post(URL+"/runes/completed", json=args).json()


# @app.route('/runes/listings', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def getRuneListings():
#     args = request.get_json()
#     rune = args.get('rune')
#     posts = RuneListing.objects(valid=True, rune=rune)
#     listings = []
#     for listing in posts:
#         listing_dict = {
#             'id': str(listing.id),
#             'type': listing.type,
#             'amount': listing.amount,
#             'price': listing.price,
#             'rune': listing.rune,
#             'symbol': listing.symbol,
#             'OrdinalAddress': listing.OrdinalAddress,
#             'PaymentAddress': listing.PaymentAddress,
#             'CounterOffers': [str(offer) for offer in listing.CounterOffers]  # Assuming CounterOffers contains non-JSON serializable objects
#         }
#         listings.append(listing_dict)
#     return jsonify(listings)


# @app.route('/runes/open-offers', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def getOpenRuneOffers():
#     args = request.get_json()
#     addr = args.get('OrdinalAddress')
#     posts = RuneListing.objects(valid=True, OrdinalAddress=addr)
#     offers = []
#     for listing in posts:
#         listing_dict = {
#             'id': str(listing.id),
#             'type': listing.type,
#             'amount': int(listing.amount),
#             'price': int(listing.price),
#             'rune': listing.rune,
#             'symbol': listing.symbol,
#             'OrdinalAddress': listing.OrdinalAddress,
#             'PaymentAddress': listing.PaymentAddress,
#             'CounterOffers': [str(offer) for offer in listing.CounterOffers]  # Assuming CounterOffers contains non-JSON serializable objects
#         }
#         offers.append(listing_dict)
#     return jsonify(offers)

# @app.route('/runes/history', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def prevRuneSales():
#     args = request.get_json()
#     rune = args.get('rune')
#     sales = RuneListing.objects(rune=rune).order_by('-time')
#     return jsonify([sale.to_mongo().to_dict() for sale in sales])

# @app.route('/runes/transfer', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def transferRune():
#     args = request.get_json()
#     runename = args['rune']
#     ordaddr = args['OrdinalAddress']
#     payaddr = args['PaymentAddress']
#     wallet = args['wallet']
#     recipient = args['recipient']
#     amount = args['amount']
#     if wallet == 'xverse':
#         pubkey = args['pubKey']
#     return requests.post(URL+"/runes/transfer", json=args).json()

# @app.route('/runes/pre-mint', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def PreMint():
#     args = request.get_json()
#     rune = args['rune']
#     fee = args['feeRate']
#     userAddress = args['OrdinalAddress']
#     try:
#         destination = args['recipient']
#     except:
#         destination = userAddress
#     refundAddress = args['PaymentAddress']
#     wallet = args['wallet']
#     if wallet=='xverse':
#         pubkey = args['pubKey']
#     repeats = args['repeats']
#     return requests.post(URL+"/runes/pre-mint", json=args).json()

# @app.route('/runes/mint', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def serverMint():
#     args = request.get_json()
#     txid = args['txid']
#     userAddress = args['OrdinalAddress']
#     if RuneListing.objects(Payment=txid).first():
#         return jsonify({'error': 'This txid was already submitted as payment for an order.'})
#     return requests.post(URL+"/runes/mint", json=args).json()

# @app.route('/runes/mint-orders', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def getMintOrders():
#     args = request.get_json()
#     userAddress = args['OrdinalAddress']
#     orders = RuneListing.objects(UserAddress=userAddress)
#     if len(orders)>0:
#         return jsonify([order.to_mongo().to_dict() for order in orders])
#     return {}

# @app.route('/runes/chart', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def runeChart():
#     args = request.get_json()
#     rune = args['rune']
#     data = RuneListing.objects(rune=rune).exclude('_id')
#     tradeInfo = RuneListing.objects(Rune=rune).exclude('_id').first()
#     return jsonify({'chart': [data1.to_mongo().to_dict() for data1 in data], 'info': tradeInfo.to_mongo().to_dict()})

# @app.route('/runes/trading-info', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def runeTradeInfo():
#     data = RuneListing.objects().order_by('-Volume').limit(25).exclude('_id')
#     return jsonify({'info': [info.to_mongo().to_dict() for info in data]})


# @app.route('/runes/total', methods=['POST','GET'])
# @cache.cached(timeout=300, query_string=True)
# def getTotal():
#     counts = RuneListing.objects().aggregate([
#         {'$group': {'_id': None, 'total': {'$sum': {'$add': ['$mints', '$trades', '$transfers']}}}}
#     ])
#     total = next(counts, {}).get('total', 0)
#     return jsonify({'total': total})

# @app.route('/runes/create-counteroffer', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def counteroffer():
#     args = request.get_json()
#     payaddr = args['PaymentAddress']
#     ordaddr = args['OrdinalAddress']
#     wallet = args['wallet']
#     price = args['price']
#     id = args['id']
#     if wallet == 'xverse':
#         pubkey = args['pubKey']
#     listing = RuneListing.objects(id=ObjectId(id)).first()
#     if (listing == None):
#         return jsonify({'error': "That listing does not exist.", 'code':error_offer_not_exist})
#     if (listing['valid'] != True):
#         return jsonify({'error':"This listing is no longer valid.", 'code': error_offer_is_invalid})
#     if price > listing['price']:
#         return jsonify({'error': "You are offering to pay more than it is listed for. Just buy normally."})
#     return requests.post(URL+"/runes/create-counteroffer", json=args).json()

# @app.route('/runes/place-counteroffer', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def counterofferPost():
#     args = request.get_json()
#     ordaddr = args.get('OrdinalAddress')
#     payaddr = args.get('PaymentAddress')
#     wallet = args.get('wallet')
#     price = args['price']
#     id = args.get('id')
#     pst = args.get('psbt')
#     listing = RuneListing.objects(id=ObjectId(id)).first()
#     if (listing == None):
#         return jsonify({'error': "That listing does not exist.", 'code':error_offer_not_exist})
#     if (listing['valid'] != True):
#         return jsonify({'error':"This listing is no longer valid.", 'code':error_offer_is_invalid})
#     return requests.post(URL+"/runes/place-counteroffer", json=args).json()

# @app.route('/runes/complete-counteroffer', methods=['POST'])
# @cache.cached(timeout=300, query_string=True)
# def CompleteCounterOffer():
#     args = request.get_json()
#     id = args.get('id')
#     txid = args.get('txid')
#     wallet = args.get('wallet')
#     listing = RuneListing.objects(id=ObjectId(id)).first()
#     if (listing == None):
#         return jsonify({'error': "That listing does not exist.", 'code':error_offer_not_exist})
#     if (listing['valid'] != True):
#         return jsonify({'error':"This listing is no longer valid.", 'code':error_offer_is_invalid}) 
#     return requests.post(URL+"/runes/complete-counteroffer", json=args).json()

if __name__ == "__main__":
    app.run(debug=True)
