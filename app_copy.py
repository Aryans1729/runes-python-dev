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
from model.model import Rune, Points, MintOrder, ChartData, Counts,RuneListing, CounterOffer, RuneSale, TradingInfo
from flask_limiter import Limiter
from flask_restx import Api, Resource, fields
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_socketio import SocketIO, emit
import logging
import secrets
from mongoengine import Document, StringField, DateTimeField, IntField, FloatField, BooleanField, ListField
import datetime
from flask_restx import fields, marshal

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
# socketio = SocketIO(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# Configure Sentry
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_URI"),
    integrations=[FlaskIntegration()],
    release=os.environ.get("VERSION"),
    enable_tracing=True,
)
URL = "https://testnet-backend-ivoa.onrender.com"
api_keys = {'api_key': 'rune@python'}


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

# Configure Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per day", "10 per hour"]
)
limiter.init_app(app)

# Configure CORS
cors = CORS(app, origins=[
    'https://mint-iz3y.onrender.com/en/mint-runes', 'https://mint-iz3y.onrender.com/', 'https://mint-iz3y.onrender.com', 'mint-iz3y.onrender.com/',
    'localhost:3000', 'https://localhost:3000', 'https://development-3mci.onrender.com/', 'http://localhost:3000', 'https://rune-frontend.onrender.com',
    'https://rune-frontend-2.onrender.com', 'https://development.runepro.com', 'https://development.onrender.com', 'https://rune-dashboard.onrender.com',
    'http://localhost:5500/', 'http://localhost:8888', 'https://runepro-test.vercel.app', 'https://runepro.com', 'https://www.runepro.com',
    'https://testnet.runepro.com', 'https://rune-frontend-1.onrender.com', 'https://development-3mci.onrender.com/'
])



@api.route('/generate_api_key')
class GenerateApiKey(Resource):
    def post(self):
        new_api_key = secrets.token_hex(16)
        api_key_entry = APIKey(key=new_api_key)
        api_key_entry.save()
        return jsonify({'api_key': new_api_key})

# Decorator function to require API key authentication
def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or not APIKey.objects(key=api_key).first():
            app.logger.debug("Unauthorized access attempt with API key: %s", api_key)
            return jsonify({'error': 'Unauthorized'}), 401
        return func(*args, **kwargs)
    return wrapper

# Error handling codes
error_codes = {
    "missing_info": "RP101",
    "missing_inscription": "RP102",
    "offer_already_exist": "RP106",
    "offer_not_exist": "RP108",
    "offer_is_invalid": "RP109",
    "invalid": "RP103",
    "wallet": "RP104",
    "misc": "RP105",
    "not_enough_balance": "RP107",
    "missing_setup": "RP110"
}

# Define API models
fee_rates_model = api.model('FeeRates', {
    'fastest': fields.Float(description='Fastest fee rate'),
    'halfHour': fields.Float(description='Fee rate for next half hour'),
    'hour': fields.Float(description='Fee rate for next hour')
})

# Define a model for the request parameters
pagination_params = api.model('Pagination', {
    'page': fields.Integer(description='Page number', example=1, default=1),
    'limit': fields.Integer(description='Number of items per page', example=10, default=10),
    'search': fields.String(description='Search query', example='example search term', default=''),

})

# Define a model for the response metadata
metadata_model = api.model('Metadata', {
    'pageNumber': fields.Integer(description='Current page number'),
    'perPage': fields.Integer(description='Number of items per page'),
    'pageCount': fields.Integer(description='Number of items on the current page'),
    'totalCount': fields.Integer(description='Total number of items'),
    'numOfPages': fields.Integer(description='Total number of pages')
})

# # Define the model for a single rune
# rune_model = api.model('Rune', {
#     # '_id': fields.String(description='Rune ID'),
#     'SpacedRune': fields.String(description='Spaced rune string'),
#     'Created': fields.DateTime(description='Creation date'),
#     'Divisibility': fields.Integer(description='Divisibility'),
#     'EtchTx': fields.String(description='Etch transaction'),
#     'LimitPerMint': fields.Integer(description='Limit per mint'),
#     'MaxMintNumber': fields.Integer(description='Maximum mint number'),
#     'MintEndAfter': fields.DateTime(description='Mint end after'),
#     'MintEndBlock': fields.Integer(description='Mint end block'),
#     'MintStartBlock': fields.Integer(description='Mint start block'),
#     'Minted': fields.Integer(description='Minted count'),
#     'Premine': fields.Integer(description='Premine count'),
#     'Progress': fields.Float(description='Progress'),
#     'RuneID': fields.String(description='Rune ID'),
#     'Supply': fields.Integer(description='Supply'),
#     'Symbol': fields.String(description='Symbol'),
#     'Mintable': fields.Boolean(description='Mintable status'),
# })
# Define the rune model for marshalling
rune_model = api.model('Rune', {
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
    # Add other fields as necessary
})

# Define a model for the response data
response_model = api.model('Response', {
    'runes': fields.List(fields.Nested(rune_model), description='List of runes'),
    'metadata': fields.Nested(metadata_model, description='Metadata for the response')
})

points_model = api.model('Points', {
    'address': fields.String(description='Address of the rune'),
    'points': fields.Integer(description='Points associated with the address')
})

response_model1 = api.model('PointsResponse', {
    'points': fields.List(fields.Nested(points_model), description='List of points'),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})


balance_response_model = api.model('BalanceResponse', {
    'balance': fields.List(fields.Nested(points_model), description='List of balances'),
    'metadata': fields.Nested(metadata_model, description='Metadata for the response')
})

# Define API models
make_psbt_model = api.model('MakePSBT', {
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'rune': fields.String(required=True, description='Rune identifier'),
    'amount': fields.Float(required=True, description='Amount'),
    'price': fields.Float(required=True, description='Price'),
    'wallet': fields.String(required=True, description='Wallet'),
    'type': fields.String(required=True, description='Type')
})

# Define API models
make_listing_model = api.model('MakeListing', {
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'rune': fields.String(required=True, description='Rune identifier'),
    'amount': fields.Float(required=True, description='Amount'),
    'price': fields.Float(required=True, description='Price'),
    'wallet': fields.String(required=True, description='Wallet'),
    'type': fields.String(required=True, description='Type'),
    'psbt': fields.String(required=True, description='PSBT')
})

# Define API models
complete_listing_model = api.model('CompleteListing', {
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'wallet': fields.String(required=True, description='Wallet'),
    'id': fields.String(required=True, description='Listing ID'),
    'pubKey': fields.String(required=False, description='Public key if wallet is xverse')
})

# Define API models
completed_rune_model = api.model('CompletedRune', {
    'id': fields.String(required=True, description='Listing ID'),
    'txid': fields.String(required=True, description='Transaction ID')
})


rune_listing_model = api.model('RuneListing', {
    'id': fields.String(description='Listing ID'),
    'type': fields.String(description='Type of listing'),
    'amount': fields.Float(description='Amount'),
    'price': fields.Float(description='Price'),
    'rune': fields.String(description='Rune'),
    'symbol': fields.String(description='Symbol'),
    'OrdinalAddress': fields.String(description='Ordinal address'),
    'PaymentAddress': fields.String(description='Payment address'),
    'CounterOffers': fields.List(fields.String, description='List of counter offers')
})

listing_response_model = api.model('ListingResponse', {
    'listings': fields.List(fields.Nested(rune_listing_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

rune_offer_model = api.model('RuneOffer', {
    'id': fields.String(description='Offer ID'),
    'type': fields.String(description='Type of offer'),
    'amount': fields.Float(description='Amount'),
    'price': fields.Float(description='Price'),
    'rune': fields.String(description='Rune'),
    'symbol': fields.String(description='Symbol'),
    'OrdinalAddress': fields.String(description='Ordinal address'),
    'PaymentAddress': fields.String(description='Payment address'),
    'CounterOffers': fields.List(fields.String, description='List of counter offers')
})

offer_response_model = api.model('OfferResponse', {
    'offers': fields.List(fields.Nested(rune_offer_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

rune_history_model = api.model('RuneHistory', {
    'txid': fields.String(description='Transaction ID'),
    'TakerPaymentAddress': fields.String(description='Taker payment address'),
    'TakerOrdinalAddress': fields.String(description='Taker ordinal address'),
    'TakerWallet': fields.String(description='Taker wallet'),
    'MakerPaymentAddress': fields.String(description='Maker payment address'),
    'MakerOrdinalAddress': fields.String(description='Maker ordinal address'),
    'MakerWallet': fields.String(description='Maker wallet'),
    'amount': fields.Float(description='Amount'),
    'price': fields.Float(description='Price'),
    'rune': fields.String(description='Rune identifier'),
    'type': fields.String(description='Transaction type'),
    'time': fields.DateTime(description='Transaction time')
})

history_response_model = api.model('HistoryResponse', {
    'sales': fields.List(fields.Nested(rune_history_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

# Define API models
transfer_model = api.model('Transfer', {
    'rune': fields.String(required=True, description='Rune name'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'wallet': fields.String(required=True, description='Wallet'),
    'recipient': fields.String(required=True, description='Recipient address'),
    'amount': fields.Float(required=True, description='Amount to transfer'),
    'pubKey': fields.String(description='Public key, required if wallet is xverse')
})

# Define API models
premint_model = api.model('PreMint', {
    'rune': fields.String(required=True, description='Rune name'),
    'feeRate': fields.Float(required=True, description='Fee rate'),
    'OrdinalAddress': fields.String(required=True, description='User ordinal address'),
    'recipient': fields.String(description='Recipient address'),
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'wallet': fields.String(required=True, description='Wallet type'),
    'pubKey': fields.String(description='Public key if wallet is xverse'),
    'repeats': fields.Integer(required=True, description='Number of repeats')
})

# Define API models for Swagger
mint_model = api.model('Mint', {
    'txid': fields.String(required=True, description='Transaction ID'),
    'OrdinalAddress': fields.String(required=True, description='User ordinal address')
})

mint_order_model = api.model('MintOrder', {
    'id': fields.String(description='Order ID'),
    'UserAddress': fields.String(description='User address'),
    'ServerAddress': fields.String(description='Server address'),
    'TotalFee': fields.Integer(description='Total fee'),
    'Repeats': fields.Integer(description='Number of repeats'),
    'Rune': fields.String(description='Rune identifier'),
    'Destination': fields.String(description='Destination address'),
    'FeeRate': fields.Integer(description='Fee rate'),
    'Remaining': fields.Integer(description='Remaining amount'),
    'Paid': fields.Boolean(description='Payment status'),
    'Completed': fields.Boolean(description='Completion status'),
    'TxIDs': fields.List(fields.String, description='List of transaction IDs'),
    'TimeCompleted': fields.DateTime(description='Time completed'),
    'TimeUpdated': fields.DateTime(description='Time updated')
})

mint_orders_response_model = api.model('MintOrdersResponse', {
    'orders': fields.List(fields.Nested(mint_order_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

rune_chart_model = api.model('RuneChart', {
    'chart': fields.List(fields.Raw, description='Chart data'),
    'info': fields.Raw(description='Trade info')
})

@app.route('/throwerror')
def throw_error(): 
    1/0  # raises an error
    return "<p>Hello, World!</p>"


@api.route('/getfeerates')
class GetFeeRatesResource(Resource):
    @api.doc(description='Get the current fee rates')
    @api.marshal_with(fee_rates_model)
    @cache.cached(timeout=300)
    @require_api_key
    @limiter.limit("5 per minute")
    def get(self):
        try:
            response = requests.get(URL + "/getfeerates")
            response.raise_for_status()
            fee_rates = response.json()

            # Emit event to WebSocket clients
            socketio.emit('fee_rates_retrieved', fee_rates)

            return fee_rates
        except requests.RequestException as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Failed to retrieve fee rates', 'message': str(e)}), 500


@app.route('/')
def hello_world():
    return 'Hello, friend!'

@api.route('/runes/points')
class PointsResource(Resource):
    @api.doc(description='Get points associated with an address')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(response_model1)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = int(args.get('page', 1))
            limit = int(args.get('limit', 10))
            search_query = args.get('search', '')
            addr = args.get('OrdinalAddress')
            skip = (page - 1) * limit

            app.logger.debug(f"Received request with search: {search_query} and OrdinalAddress: {addr}")

            # Construct the query
            query = Q()
            if search_query:
                query &= Q(address__icontains=search_query)
            if addr:
                query &= Q(address=addr)

            app.logger.debug(f"Constructed query: {query}")

            # Fetch the points
            points_objects = Points.objects(query).skip(skip).limit(limit)
            points_list = [{'address': obj.address, 'points': obj.points} for obj in points_objects]
            total_count = Points.objects(query).count()

            app.logger.debug(f"Fetched {len(points_list)} points")
            app.logger.debug(f"Total count: {total_count}")

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(points_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            response_data = {
                "points": points_list,
                "metadata": metadata
            }

            # Emit event to WebSocket clients
            socketio.emit('points_retrieved', response_data)

            # Log the query and result for debugging
            app.logger.debug(f"Response data: {response_data}")

            return response_data
        except Exception as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Internal server error")
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

# @api.route('/runes/points')
# class PointsResource(Resource):
#     @api.doc(description='Get points associated with an address')
#     @api.expect(pagination_params, validate=True)
#     @api.marshal_with(response_model1)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             page = int(args.get('page', 1))
#             limit = int(args.get('limit', 793))
#             search_query = args.get('search', '')
#             addr = args.get('OrdinalAddress')
#             skip = (page - 1) * limit

#             # Enhanced search capabilities
#             query = Q(address__icontains=search_query)
#             if addr:
#                 query &= Q(address=addr)

#             points_objects = Points.objects(query).skip(skip).limit(limit)
#             points_list = [{'points': obj.points} for obj in points_objects]
#             total_count = Points.objects(query).count()

#             metadata = {
#                 "pageNumber": page,
#                 "perPage": limit,
#                 "pageCount": len(points_list),
#                 "totalCount": total_count,
#                 "numOfPages": math.ceil(total_count / limit)
#             }

#             response_data = {
#                 "points": points_list,
#                 "metadata": metadata
#             }

#             # Emit event to WebSocket clients
#             socketio.emit('points_retrieved', response_data)

#             return response_data
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


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
            regex_query = Q(SpacedRune__icontains=search_query) | Q(Symbol__icontains=search_query)
            runes = Rune.objects(regex_query).skip(skip).limit(limit)
            runelist = []
            for rune in runes:
                rune_dict = rune.to_mongo().to_dict()
                rune_dict['_id'] = str(rune_dict['_id'])
                runelist.append(rune_dict)
            total_count = Rune.objects(regex_query).count()
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

            # Emit event to WebSocket clients
            socketio.emit('runes_retrieved', response_data)

            return response_data
        except Exception as e:
            sentry_sdk.capture_exception(e)
            api.abort(500, f"Internal server error: {str(e)}")

@api.route('/rune')
class SingleRuneInfoResource(Resource):
    @api.doc(description='Get information about a single rune')
    @api.expect(api.model('RuneSearch', {
        'rune': fields.String(required=True, description='Name or ID of the rune to search for')
    }), validate=True)
    @api.marshal_with(rune_model, as_list=False)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            name = args['rune']
            search_fields = ['SpacedRune', 'RuneID', 'Symbol']  # Example additional fields for search
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": name})
            
            rune = Rune.objects(query).first()
            if not rune:
                return {'error': 'Rune not found'}, 404
            
            rune_dict = rune.to_mongo().to_dict()
            # Convert MongoDB date format to Python datetime object
            if 'Created' in rune_dict and isinstance(rune_dict['Created'], dict) and '$date' in rune_dict['Created']:
                rune_dict['Created'] = datetime.fromtimestamp(rune_dict['Created']['$date'] / 1000)
            
            socketio.emit('rune_info_retrieved', rune_dict)  # Notify clients about the retrieval
            return marshal(rune_dict, rune_model)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            api.abort(500, f"Internal server error: {str(e)}")
# @api.route('/rune')
# class SingleRuneInfoResource(Resource):
#     @api.doc(description='Get information about a single rune')
#     @api.expect(response_model, validate=True)
#     @api.marshal_with(rune_model, as_list=False)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             name = args['rune']
#             search_fields = ['SpacedRune', 'RuneID', 'Symbol']  # Example additional fields for search
#             query = Q()
#             for field in search_fields:
#                 query |= Q(**{f"{field}__icontains": name})
#             rune = Rune.objects(query).exclude('_id').first()
#             if not rune:
#                 return {'error': 'Rune not found'}, 404
#             rune_json = json.loads(rune.to_json())
#             socketio.emit('rune_info_retrieved', rune_json)  # Notify clients about the retrieval
#             return rune_json
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             api.abort(500, f"Internal server error: {str(e)}")


@api.route('/runes/balance')
class RuneBalanceResource(Resource):
    @api.doc(description='Get the balance of a rune')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(balance_response_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            addr = args.get('OrdinalAddress')
            page = int(args.get('page', 1))
            limit = int(args.get('limit', 10))
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(address__icontains=search_query)
            if addr:
                query &= Q(address=addr)

            points_objects = Points.objects(query).skip(skip).limit(limit)
            points_list = [{'address': obj.address, 'points': obj.points} for obj in points_objects]
            total_count = Points.objects(query).count()

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(points_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit balance data to connected WebSocket clients
            socketio.emit('balance_retrieved', {'address': addr, 'balance': points_list, 'metadata': metadata})

            return {'balance': points_list, 'metadata': metadata}
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return {'error': 'Internal server error', 'message': str(e)}, 500

# @api.route('/runes/balance')
# class RuneBalanceResource(Resource):
#     @api.doc(description='Get the balance of a rune')
#     @api.expect(pagination_params, validate=True)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             addr = args['OrdinalAddress']
#             page = int(request.args.get('page', 1))
#             limit = int(request.args.get('limit', 10))
#             skip = (page - 1) * limit

#             # Assuming that the external API supports pagination
#             response = requests.post(URL + "/runes/balance", json={'OrdinalAddress': addr, 'skip': skip, 'limit': limit})
#             if response.status_code != 200:
#                 return jsonify({'error': 'Failed to retrieve balance'}), response.status_code

#             result = response.json()
#             total_count = result.get('totalCount', 0)  # Assuming the external API returns total count
#             balance_data = result.get('data', [])
#             metadata = {
#                 "pageNumber": page,
#                 "perPage": limit,
#                 "pageCount": len(balance_data),
#                 "totalCount": total_count,
#                 "numOfPages": math.ceil(total_count / limit)
#             }

#             # Emit balance data to connected WebSocket clients
#             socketio.emit('balance_retrieved', {'address': addr, 'balance': balance_data, 'metadata': metadata})

#             return jsonify({'balance': balance_data, 'metadata': metadata})
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/make-psbt')
class MakePSBTResource(Resource):
    @api.doc(description='Create a PSBT for a rune')
    @api.expect(make_psbt_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            payaddr = args['PaymentAddress']
            ordaddr = args['OrdinalAddress']
            rune = args['rune']
            amount = float(args['amount'])
            price = float(args['price'])
            wallet = args['wallet']
            typ = args['type']

            response = requests.post(URL + "/runes/make-psbt", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to create PSBT'}), response.status_code

            psbt_data = response.json()
            
            # Emit PSBT data to connected WebSocket clients
            socketio.emit('psbt_created', {'data': psbt_data})

            return jsonify(psbt_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        



@api.route('/runes/make-listing')
class MakeListingResource(Resource):
    @api.doc(description='Create a listing for a rune')
    @api.expect(make_listing_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            payaddr = args['PaymentAddress']
            ordaddr = args['OrdinalAddress']
            rune = args['rune']
            amount = float(args['amount'])
            price = float(args['price'])
            wallet = args['wallet']
            typ = args['type']
            pst = args['psbt']

            response = requests.post(URL + "/runes/make-listing", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to create listing'}), response.status_code

            listing_data = response.json()
            
            # Emit listing data to connected WebSocket clients
            socketio.emit('listing_created', {'data': listing_data})

            return jsonify(listing_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500



@api.route('/runes/complete-listing')
class CompleteListingResource(Resource):
    @api.doc(description='Complete a PSBT for a rune listing')
    @api.expect(complete_listing_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            payaddr = args['PaymentAddress']
            ordaddr = args['OrdinalAddress']
            wallet = args['wallet']
            listing_id = args['id']
            pubkey = args.get('pubKey') if wallet == 'xverse' else None

            response = requests.post(URL + "/runes/complete-listing", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete listing'}), response.status_code

            listing_data = response.json()

            # Emit listing completion data to connected WebSocket clients
            socketio.emit('listing_completed', {'data': listing_data})

            return jsonify(listing_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500



@api.route('/runes/completed')
class CompletedRuneResource(Resource):
    @api.doc(description='Mark a rune listing as completed')
    @api.expect(completed_rune_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            _id = args.get('id')
            txid = args.get('txid')

            # Query for the listing using mongoengine
            listing = RuneListing.objects(id=ObjectId(_id)).first()

            # Error handling
            if listing is None:
                return jsonify({'error': "That listing does not exist.", 'code': error_codes['offer_not_exist']})
            if not listing.valid:
                return jsonify({'error': "This listing is no longer valid.", 'code': error_codes['offer_is_invalid']})

            # Forward the request if the listing is valid
            response = requests.post(URL + "/runes/completed", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to complete listing'}), response.status_code

            completed_data = response.json()

            # Emit completed listing data to connected WebSocket clients
            socketio.emit('listing_completed', {'data': completed_data})

            return jsonify(completed_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/listings')
class RuneListingsResource(Resource):
    @api.doc(description='Get a list of rune listings with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(listing_response_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(valid=True)
            if 'rune' in args:
                query &= Q(rune__icontains=args['rune'])
            if search_query:
                query &= (Q(rune__icontains=search_query) | Q(symbol__icontains=search_query) | Q(type__icontains=search_query))

            posts = RuneListing.objects(query).skip(skip).limit(limit)
            total_count = RuneListing.objects(query).count()
            listings = []
            for listing in posts:
                listing_dict = {
                    'id': str(listing.id),
                    'type': listing.type,
                    'amount': listing.amount,
                    'price': listing.price,
                    'rune': listing.rune,
                    'symbol': listing.symbol,
                    'OrdinalAddress': listing.OrdinalAddress,
                    'PaymentAddress': listing.PaymentAddress,
                    'CounterOffers': [str(offer) for offer in listing.CounterOffers]  # Assuming CounterOffers contains non-JSON serializable objects
                }
                listings.append(listing_dict)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(listings),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit listings data to connected WebSocket clients
            socketio.emit('listings_retrieved', {'listings': listings, 'metadata': metadata})

            return {'listings': listings, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

@api.route('/runes/open-offers')
class RuneOpenOffersResource(Resource):
    @api.doc(description='Get open offers for a rune with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(offer_response_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            addr = args.get('OrdinalAddress')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(valid=True) & Q(OrdinalAddress=addr)
            if search_query:
                query &= (Q(rune__icontains=search_query) | Q(symbol__icontains=search_query) | Q(type__icontains=search_query))

            posts = RuneListing.objects(query).skip(skip).limit(limit)
            total_count = RuneListing.objects(query).count()
            offers = []
            for listing in posts:
                listing_dict = {
                    'id': str(listing.id),
                    'type': listing.type,
                    'amount': listing.amount,
                    'price': listing.price,
                    'rune': listing.rune,
                    'symbol': listing.symbol,
                    'OrdinalAddress': listing.OrdinalAddress,
                    'PaymentAddress': listing.PaymentAddress,
                    'CounterOffers': [str(offer) for offer in listing.CounterOffers]  # Assuming CounterOffers contains non-JSON serializable objects
                }
                offers.append(listing_dict)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(offers),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit offers data to connected WebSocket clients
            socketio.emit('offers_retrieved', {'offers': offers, 'metadata': metadata})

            return {'offers': offers, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/history')
class RuneHistoryResource(Resource):
    @api.doc(description='Get the history of rune sales with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(history_response_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            rune = args.get('rune')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(rune=rune)
            if search_query:
                query &= (Q(rune__icontains=search_query) | Q(type__icontains=search_query))

            sales = RuneSale.objects(query).order_by('-time').skip(skip).limit(limit)
            total_count = RuneSale.objects(query).count()
            sales_list = []
            for sale in sales:
                sale_dict = sale.to_mongo().to_dict()
                sale_dict['_id'] = str(sale_dict['_id'])
                sales_list.append(sale_dict)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(sales_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit sales data to connected WebSocket clients
            socketio.emit('history_retrieved', {'sales': sales_list, 'metadata': metadata})

            return {'sales': sales_list, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/transfer')
class TransferRuneResource(Resource):
    @api.doc(description='Transfer a rune to another address')
    @api.expect(transfer_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            runename = args['rune']
            ordaddr = args['OrdinalAddress']
            payaddr = args['PaymentAddress']
            wallet = args['wallet']
            recipient = args['recipient']
            amount = args['amount']
            if wallet == 'xverse':
                pubkey = args['pubKey']
            response = requests.post(URL + "/runes/transfer", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to transfer rune'}), response.status_code

            transfer_data = response.json()

            # Emit transfer data to connected WebSocket clients
            socketio.emit('rune_transferred', {'data': transfer_data})

            return jsonify(transfer_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

@api.route('/runes/pre-mint')
class PreMintResource(Resource):
    @api.doc(description='Pre-mint a rune')
    @api.expect(premint_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            rune = args['rune']
            fee = args['feeRate']
            userAddress = args['OrdinalAddress']
            destination = args.get('recipient', userAddress)
            refundAddress = args['PaymentAddress']
            wallet = args['wallet']
            if wallet == 'xverse':
                pubkey = args['pubKey']
            repeats = args['repeats']
            response = requests.post(URL + "/runes/pre-mint", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to pre-mint rune'}), response.status_code

            premint_data = response.json()

            # Emit pre-mint data to connected WebSocket clients
            socketio.emit('rune_pre_minted', {'data': premint_data})

            return jsonify(premint_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

@api.route('/runes/mint')
class MintRuneResource(Resource):
    @api.doc(description='Mint a rune')
    @api.expect(mint_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            txid = args['txid']
            userAddress = args['OrdinalAddress']
            if MintOrder.objects(TxIDs=txid).first():
                return jsonify({'error': 'This txid was already submitted as payment for an order.'}), 400
            response = requests.post(URL + "/runes/mint", json=args)
            if response.status_code != 200:
                return jsonify({'error': 'Failed to mint rune'}), response.status_code

            mint_data = response.json()

            # Emit mint data to connected WebSocket clients
            socketio.emit('rune_minted', {'data': mint_data})

            return jsonify(mint_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

@api.route('/runes/mint-orders')
class MintOrdersResource(Resource):
    @api.doc(description='Get mint orders for a user with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(mint_orders_response_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            userAddress = args['OrdinalAddress']
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(UserAddress=userAddress)
            if search_query:
                query &= (Q(Rune__icontains=search_query) | Q(ServerAddress__icontains=search_query) | Q(Destination__icontains=search_query))

            orders = MintOrder.objects(query).skip(skip).limit(limit)
            total_count = MintOrder.objects(query).count()
            orders_list = []
            for order in orders:
                order_dict = order.to_mongo().to_dict()
                order_dict['_id'] = str(order_dict['_id'])
                orders_list.append(order_dict)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(orders_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit orders data to connected WebSocket clients
            socketio.emit('mint_orders_retrieved', {'orders': orders_list, 'metadata': metadata})

            return {'orders': orders_list, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/chart')
class RuneChartResource(Resource):
    @api.doc(description='Get rune chart data with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(rune_chart_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            rune = args['rune']
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q(rune=rune)
            if search_query:
                query &= (Q(rune__icontains=search_query))

            data = ChartData.objects(query).skip(skip).limit(limit).exclude('_id')
            tradeInfo = ChartData.objects(rune=rune).exclude('_id').first()
            total_count = ChartData.objects(query).count()
            chart_data = [data1.to_mongo().to_dict() for data1 in data]

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(chart_data),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit chart data to connected WebSocket clients
            socketio.emit('chart_data_retrieved', {'chart': chart_data, 'info': tradeInfo.to_mongo().to_dict(), 'metadata': metadata})

            return {'chart': chart_data, 'info': tradeInfo.to_mongo().to_dict()}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


trading_info_model = api.model('TradingInfo', {
    'info': fields.List(fields.Raw, description='Trading information')
})

@api.route('/runes/trading-info')
class RuneTradingInfoResource(Resource):
    @api.doc(description='Get trading information for runes with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(trading_info_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q()
            if search_query:
                query &= (Q(Rune__icontains=search_query) | Q(Symbol__icontains=search_query))

            data = TradingInfo.objects(query).order_by('-Supply').skip(skip).limit(limit).exclude('_id')
            total_count = TradingInfo.objects(query).count()
            trading_info = [info.to_mongo().to_dict() for info in data]

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(trading_info),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit trading info to connected WebSocket clients
            socketio.emit('trading_info_retrieved', {'info': trading_info, 'metadata': metadata})

            return {'info': trading_info}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

# total_model = api.model('Total', {
#     'total': fields.Integer(description='Total count')
# })

# @api.route('/runes/total')
# class RuneTotalResource(Resource):
#     @api.doc(description='Get the total number of mints, trades, and transfers')
#     @api.marshal_with(total_model)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             counts = RuneListing.objects().aggregate([
#                 {'$group': {'_id': None, 'total': {'$sum': {'$add': ['$mints', '$trades', '$transfers']}}}}
#             ])
#             total = next(counts, {}).get('total', 0)

#             # Emit total data to connected WebSocket clients
#             socketio.emit('total_retrieved', {'total': total})

#             return {'total': total}
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


total_model = api.model('Total', {
    'total': fields.List(fields.Raw, description='Total count'),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

@api.route('/runes/total')
class RuneTotalResource(Resource):
    @api.doc(description='Get the total number of mints, trades, and transfers')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(total_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            match_stage = {}
            if search_query:
                match_stage = {'$match': {'rune': {'$regex': search_query, '$options': 'i'}}}

            pipeline = [
                match_stage,
                {'$group': {'_id': None, 'total': {'$sum': {'$add': ['$mints', '$trades', '$transfers']}}}},
                {'$sort': {'total': -1}},
                {'$skip': skip},
                {'$limit': limit}
            ]

            counts = Counts.objects.aggregate(pipeline)
            total_list = list(counts)

            total_count = Counts.objects.aggregate([
                match_stage,
                {'$count': 'totalCount'}
            ])
            total_count = next(total_count, {}).get('totalCount', 0)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(total_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit total data to connected WebSocket clients
            socketio.emit('total_retrieved', {'totals': total_list, 'metadata': metadata})

            return {'total': total_list, 'metadata': metadata}
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        
        

counteroffer_list_model = api.model('CounterOfferList', {
    'counteroffers': fields.List(fields.Raw, description='List of counteroffers'),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

@api.route('/runes/counteroffers')
class CounterOfferListResource(Resource):
    @api.doc(description='Get a list of counteroffers with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(counteroffer_list_model)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            # Enhanced search capabilities
            query = Q()
            if search_query:
                query &= (Q(OrdinalAddress__icontains=search_query) | Q(PaymentAddress__icontains=search_query) | Q(wallet__icontains=search_query))

            counteroffers = CounterOffer.objects(query).skip(skip).limit(limit)
            total_count = CounterOffer.objects(query).count()
            counteroffer_list = [counteroffer.to_mongo().to_dict() for counteroffer in counteroffers]

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(counteroffer_list),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            # Emit counteroffer data to connected WebSocket clients
            socketio.emit('counteroffers_retrieved', {'counteroffers': counteroffer_list, 'metadata': metadata})

            return {'counteroffers': counteroffer_list, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


# Example of placing a counteroffer
place_counteroffer_model = api.model('PlaceCounterOffer', {
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'wallet': fields.String(required=True, description='Wallet type'),
    'price': fields.Float(required=True, description='Price'),
    'id': fields.String(required=True, description='Listing ID'),
    'psbt': fields.String(required=True, description='Partially signed Bitcoin transaction')
})

@api.route('/runes/place-counteroffer')
class PlaceCounterOfferResource(Resource):
    @api.doc(description='Place a counteroffer for a rune listing')
    @api.expect(place_counteroffer_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            ordaddr = args.get('OrdinalAddress')
            payaddr = args.get('PaymentAddress')
            wallet = args.get('wallet')
            price = args['price']
            id = args.get('id')
            pst = args.get('psbt')
            listing = RuneListing.objects(id=ObjectId(id)).first()
            if listing is None:
                return jsonify({'error': "That listing does not exist.", 'code': error_codes['offer_not_exist']}), 404
            if not listing['valid']:
                return jsonify({'error': "This listing is no longer valid.", 'code': error_codes['offer_is_invalid']}), 400
            
            # Emit counteroffer placement to connected WebSocket clients
            socketio.emit('counteroffer_placed', {'listing_id': id, 'price': price, 'ordinal_address': ordaddr})

            return requests.post(URL + "/runes/place-counteroffer", json=args).json()
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


# Define API models
complete_counteroffer_model = api.model('CompleteCounterOffer', {
    'id': fields.String(required=True, description='Listing ID'),
    'txid': fields.String(required=True, description='Transaction ID'),
    'wallet': fields.String(required=True, description='Wallet type')
})

@api.route('/runes/complete-counteroffer')
class CompleteCounterOfferResource(Resource):
    @api.doc(description='Complete a counteroffer for a rune listing')
    @api.expect(complete_counteroffer_model, validate=True)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            id = args.get('id')
            txid = args.get('txid')
            wallet = args.get('wallet')
            listing = RuneListing.objects(id=ObjectId(id)).first()
            if listing is None:
                return jsonify({'error': "That listing does not exist.", 'code': error_codes['offer_not_exist']}), 404
            if not listing['valid']:
                return jsonify({'error': "This listing is no longer valid.", 'code': error_codes['offer_is_invalid']}), 400
            
            # Emit counteroffer completion to connected WebSocket clients
            socketio.emit('counteroffer_completed', {'listing_id': id, 'txid': txid})

            return requests.post(URL + "/runes/complete-counteroffer", json=args).json()
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
        

# Notification service with WebSockets
@socketio.on('connect')
def handle_connect():
    emit('response', {'message': 'Connected to notification service'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    emit('response', {'message': 'Message received', 'data': data}, broadcast=True)

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    socketio.run(app, debug=True, log_output=True)
