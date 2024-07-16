from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, fields, marshal
from flask_caching import Cache
from flask_socketio import SocketIO, emit
from mongoengine import connect, Q
from functools import wraps
import mongoengine as me
import requests
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import datetime
import os
import math
import secrets
import logging
import certifi
from dotenv import load_dotenv
import uuid
from model.model1 import Rune, Points, Chart, Counts, RuneListing, RuneSale, TradingInfo, APIKey,MintOrder
from datetime import datetime
import datetime
from redis import Redis
from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField, ListField, connect
# 
# Load environment variables
load_dotenv()


app = Flask(__name__)
api = Api(app, version='1.0', title='Rune API', description='APIs to manage runes', doc='/docs')
socketio = SocketIO(app, cors_allowed_origins="*")


redis_client = Redis(host='localhost', port=6380)

# Configure Flask-Caching with Redis
cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6380,
    'CACHE_REDIS_DB': 0,
    'CACHE_REDIS_URL': 'redis://localhost:6380/0'
})

cache.init_app(app)
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
        connect(
            db="test_database",  # replace with your database name
            host="mongodb+srv://aryanksharma1729:runes%401729@atlascluster.aewcgmd.mongodb.net/test_database",
            tlsCAFile=certifi.where() if os.getenv("USE_TLS", "false").lower() == "true" else None
        )
        print("Connected to DB. Server status: MongoDB")
    except Exception as e:
        print("Failed to connect to DB:", str(e))

check_db_connection()



# Configure Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    app=app,
    storage_uri="redis://localhost:6380"
)
limiter.init_app(app)

# Configure CORS
cors = CORS(app, origins=[
    'https://mint-iz3y.onrender.com', 'http://localhost:3000', 'https://rune-frontend.onrender.com',
    'https://development.runepro.com', 'https://rune-dashboard.onrender.com', 'http://localhost:5500',
    'http://localhost:8888', 'https://runepro-test.vercel.app', 'https://runepro.com'
])

# Decorator function to require API key authentication
# def require_api_key(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         api_key = request.headers.get('x-api-key')
#         if not api_key or not APIKey.objects(key=api_key).first():
#             app.logger.debug("Unauthorized access attempt with API key: %s", api_key)
#             return jsonify({'error': 'Unauthorized'}), 401
#         return func(*args, **kwargs)
#     return wrapper


def require_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return jsonify({"message": "API key is missing"}), 401
        
        auth_header = request.headers['Authorization']
        if not auth_header.startswith("Bearer "):
            return jsonify({"message": "Invalid API key format"}), 401
        
        api_key = auth_header.split("Bearer ")[1]
        # Replace 'APIKeyModel' with your actual model used to store API keys
        if not APIKey.objects(key=api_key).first():
            return jsonify({"message": "Invalid API key"}), 401

        return func(*args, **kwargs)
    return decorated_function

# Error handling codes
error_codes = {
    "missing_info": "RP101",
    "offer_not_exist": "RP108",
    "offer_is_invalid": "RP109",
    "invalid": "RP103",
    "misc": "RP105",
}

# Define API models
fee_rates_model = api.model('FeeRates', {
    'fastest': fields.Float(description='Fastest fee rate'),
    'halfHour': fields.Float(description='Fee rate for next half hour'),
    'hour': fields.Float(description='Fee rate for next hour')
})

pagination_params = api.model('Pagination', {
    'page': fields.Integer(description='Page number', example=1, default=1),
    'limit': fields.Integer(description='Number of items per page', example=10, default=10),
    'search': fields.String(description='Search query', example='example search term', default=''),
})

metadata_model = api.model('Metadata', {
    'pageNumber': fields.Integer(description='Current page number'),
    'perPage': fields.Integer(description='Number of items per page'),
    'pageCount': fields.Integer(description='Number of items on the current page'),
    'totalCount': fields.Integer(description='Total number of items'),
    'numOfPages': fields.Integer(description='Total number of pages')
})

# Define API models
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


response_model = api.model('Response', {
    'runes': fields.List(fields.Nested(rune_model), description='List of runes'),
    'metadata': fields.Nested(metadata_model, description='Metadata for the response')
})

rune_search_model = api.model('Rune', {
    'rune': fields.String(required=True, description='Name or ID of the rune to search for')
})


points_model = api.model('Points', {
    'address': fields.String(description='Address of the rune'),
    'points': fields.Integer(description='Points associated with the address')
})


response_model1 = api.model('PointsResponse', {
    'points': fields.List(fields.Nested(points_model), description='List of points'),
    'metadata': fields.Nested(metadata_model)
})

balance_response_model = api.model('BalanceResponse', {
    'balance': fields.List(fields.Nested(points_model), description='List of balances'),
    'metadata': fields.Nested(metadata_model)
})

make_psbt_model = api.model('MakePSBT', {
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'rune': fields.String(required=True, description='Rune identifier'),
    'amount': fields.Float(required=True, description='Amount'),
    'price': fields.Float(required=True, description='Price'),
    'wallet': fields.String(required=True, description='Wallet'),
    'type': fields.String(required=True, description='Type')
})

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

complete_listing_model = api.model('CompleteListing', {
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'wallet': fields.String(required=True, description='Wallet'),
    'id': fields.String(required=True, description='Listing ID'),
    'pubKey': fields.String(required=False, description='Public key if wallet is xverse')
})

completed_rune_model = api.model('CompletedRune', {
    'id': fields.String(required=True, description='Listing ID'),
    # 'txid': fields.String(required=True, description='Transaction ID')
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
    'CounterOffers': fields.List(fields.String, description='List of counter offers'),
    'Completed': fields.DateTime(description='Completed date'),
    'spent': fields.Integer(description='spent'),
    'Created': fields.DateTime(description='Created date')
})

listing_response_model = api.model('ListingResponse', {
    'listings': fields.List(fields.Nested(rune_listing_model)),
    'metadata': fields.Nested(metadata_model)
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
    'metadata': fields.Nested(metadata_model)
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

# history_response_model = api.model('HistoryResponse', {
#     'sales': fields.List(fields.Nested(rune_history_model)),
#     'metadata': fields.Nested(metadata_model)
# })
offer_response_model = api.model('OfferResponse', {
    'offers': fields.List(fields.Nested(rune_listing_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})

sales_model = api.model('Sale', {
    '_id': fields.String(description='Sale ID'),
    'txid': fields.String(description='Transaction ID'),
    'TakerPaymentAddress': fields.String(description='Taker Payment Address'),
    'TakerOrdinalAddress': fields.String(description='Taker Ordinal Address'),
    'TakerWallet': fields.String(description='Taker Wallet'),
    'MakerPaymentAddress': fields.String(description='Maker Payment Address'),
    'MakerOrdinalAddress': fields.String(description='Maker Ordinal Address'),
    'MakerWallet': fields.String(description='Maker Wallet'),
    'amount': fields.Float(description='Amount'),
    'price': fields.Float(description='Price'),
    'rune': fields.String(description='Rune'),
    'type': fields.String(description='Type of sale'),
    'time': fields.String(description='Time of sale')  # Use String to handle ISO format
})

history_response_model = api.model('HistoryResponse', {
    'sales': fields.List(fields.Nested(sales_model)),
    'metadata': fields.Nested(api.model('Metadata', {
        'pageNumber': fields.Integer(description='Current page number'),
        'perPage': fields.Integer(description='Number of items per page'),
        'pageCount': fields.Integer(description='Number of items on the current page'),
        'totalCount': fields.Integer(description='Total number of items'),
        'numOfPages': fields.Integer(description='Total number of pages')
    }))
})


transfer_model = api.model('Transfer', {
    'rune': fields.String(required=True, description='Rune name'),
    'OrdinalAddress': fields.String(required=True, description='Ordinal address'),
    'PaymentAddress': fields.String(required=True, description='Payment address'),
    'wallet': fields.String(required=True, description='Wallet'),
    'recipient': fields.String(required=True, description='Recipient address'),
    'amount': fields.Float(required=True, description='Amount to transfer'),
    'pubKey': fields.String(description='Public key, required if wallet is xverse')
})

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

# mint_model = api.model('MintModel', {
#     'UserAddress': fields.String(required=True, description='UserAddress'),
#     'ServerAddress': fields.String(required=True, description='ServerAddress'),
#     'TotalFee': fields.Integer(required=False, description='TotalFee'),
#     'Repeats': fields.Integer(required=False, description='Repeats'),
#     'Rune': fields.String(required=True, description='Rune'),
#     'Destination': fields.String(required=False, description='Destination'),
#     'FeeRate': fields.Integer(required=False, description='FeeRate'),
#     'Remaining': fields.Integer(required=False, description='Remaining'),
#     'Paid': fields.Boolean(required=False, description='Paid'),
#     'Completed': fields.Boolean(required=False, description='Completed'),
#     'TimeCreated': fields.DateTime(required=False, description='TimeCreated'),
#     'TxIDs': fields.List(fields.String, required=True, description='TTxIDs'),
#     'TimeCompleted': fields.DateTime(required=False, description='TimeCompleted'),
#     'TimeUpdated': fields.DateTime(required=False, description='TimeUpdated')
# })


# mint_model = api.model('MintModel', {
#     'UserAddress': fields.String(required=True, description='UserAddress'),
#     'ServerAddress': fields.String(required=True, description='ServerAddress'),
#     'TotalFee': fields.Integer(required=False, description='TotalFee'),
#     'Repeats': fields.Integer(required=False, description='Repeats'),
#     'Rune': fields.String(required=True, description='Rune'),
#     'Destination': fields.String(required=False, description='Destination'),
#     'FeeRate': fields.Integer(required=False, description='FeeRate'),
#     'Remaining': fields.Integer(required=False, description='Remaining'),
#     'Paid': fields.Boolean(required=False, description='Paid'),
#     'Completed': fields.Boolean(required=False, description='Completed'),
#     'TimeCreated': fields.DateTime(required=False, description='TimeCreated'),
#     'TxIDs': fields.List(fields.String, required=True, description='TxIDs'),
#     'TimeCompleted': fields.DateTime(required=False, description='TimeCompleted'),
#     'TimeUpdated': fields.DateTime(required=False, description='TimeUpdated')
# })


mint_model = api.model('MintModel', {
    'UserAddress': fields.String(required=True, description='User blockchain address'),
    'ServerAddress': fields.String(required=True, description='Server blockchain address'),
    'TotalFee': fields.Integer(description='Total fee for the transaction'),
    'Repeats': fields.Integer(description='Number of repeats'),
    'Rune': fields.String(required=True, description='Type of rune'),
    'Destination': fields.String(description='Destination address'),
    'FeeRate': fields.Integer(description='Fee rate applied'),
    'Remaining': fields.Integer(description='Remaining amount'),
    'Paid': fields.Boolean(description='Payment status'),
    'Completed': fields.Boolean(description='Completion status'),
    'TxIDs': fields.List(fields.String, required=True, description='Transaction IDs'),
    'TimeCreated': fields.DateTime(description='Time when created'),
    'TimeCompleted': fields.DateTime(description='Time when completed'),
    'TimeUpdated': fields.DateTime(description='Time when updated')
})


mint_order_model = api.model('MintOrder', {
    'id': fields.String(description='Order ID'),
    'UserAddress': fields.String(description='UserAddress'),
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
    'metadata': fields.Nested(metadata_model)
})

rune_chart_model = api.model('RuneChart', {
    'chart': fields.List(fields.Raw, description='Chart data'),
    'info': fields.Raw(description='Trade info')
})

# @api.route('/generate_api_key')
# class GenerateApiKey(Resource):
#     @api.doc(description='Generate a new API key')
#     def post(self):
#         new_api_key = secrets.token_hex(16)
#         api_key_entry = APIKey(key=new_api_key)
#         api_key_entry.save()
#         return jsonify({'api_key': new_api_key})


@app.route('/generate_api_key', methods=['POST'])
def generate_api_key():
    new_key = str(uuid.uuid4().hex)
    api_key = APIKey(key=new_key)
    api_key.save()
    return jsonify({"api_key": new_key})



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

import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/runes/points', methods=['POST'])
@require_api_key
def points():
    try:
        args = request.get_json()
        app.logger.debug(f"Request args: {args}")
        page = int(args.get('page', 1))
        limit = int(args.get('limit', 10))
        search_query = args.get('search', '')
        addr = args.get('OrdinalAddress')
        skip = (page - 1) * limit

        query = Q()
        if search_query:
            query &= Q(address__icontains=search_query)
        if addr:
            query &= Q(address=addr)

        points_objects = Points.objects(query).skip(skip).limit(limit)
        app.logger.debug(f"Points objects: {points_objects}")
        points_list = [{'address': obj.address, 'points': obj.points} for obj in points_objects]
        total_count = Points.objects(query).count()

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

        app.logger.debug(f"Response data: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        app.logger.exception("Internal server error")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
    
@api.route('/runes')
class RuneResource(Resource):
    @api.doc(description='Get a list of runes with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(response_model)
    @require_api_key
    def post(self):
        try:
            page = request.json.get('page', 1)
            limit = request.json.get('limit', 10)
            search_query = request.json.get('search', '')
            skip = (page - 1) * limit

            # Log the input parameters
            app.logger.debug(f"Page: {page}, Limit: {limit}, Search Query: {search_query}")

            # Construct the query
            query = Q(SpacedRune__icontains=search_query) | Q(Symbol__icontains=search_query)
            app.logger.debug(f"Executing query: {query}")

            # Execute the query
            runes = Rune.objects(query).skip(skip).limit(limit)
            app.logger.debug(f"Raw query results: {[r.to_mongo().to_dict() for r in runes]}")

            total_count = Rune.objects(query).count()
            app.logger.debug(f"Total count of matching runes: {total_count}")

            if not runes:
                app.logger.debug("No runes found for the given search query.")
                return {
                    "runes": [],
                    "metadata": {
                        "pageNumber": page,
                        "perPage": limit,
                        "pageCount": 0,
                        "totalCount": total_count,
                        "numOfPages": 0
                    }
                }, 200

            runelist = []
            for rune in runes:
                rune_dict = rune.to_mongo().to_dict()
                rune_dict['_id'] = str(rune_dict['_id'])
                runelist.append(rune_dict)

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

            app.logger.debug(f"Response data: {response_data}")

            return response_data
        except Exception as e:
            app.logger.exception("Internal server error")
            return {"message": "Internal server error"}, 500
        

@api.route('/rune')
class SingleRuneInfoResource(Resource):
    @api.doc(description='Get information about a single rune')
    @api.expect(rune_search_model, validate=True)  # Use the defined model here
    @api.marshal_with(rune_model, as_list=False)
    @cache.cached(timeout=300, query_string=True)
    @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            app.logger.debug(f"Request args: {args}")
            name = args['rune']
            search_fields = ['SpacedRune', 'RuneID', 'Symbol']
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": name})
            
            app.logger.debug(f"Query: {query}")
            rune = Rune.objects(query).first()
            app.logger.debug(f"Rune found: {rune}")

            if not rune:
                return {'error': 'Rune not found'}, 404
            
            rune_dict = rune.to_mongo().to_dict()
            app.logger.debug(f"Rune dictionary: {rune_dict}")
            
            # Convert MongoDB date format to Python datetime object
            if 'Created' in rune_dict and isinstance(rune_dict['Created'], dict) and '$date' in rune_dict['Created']:
                rune_dict['Created'] = datetime.datetime.fromtimestamp(rune_dict['Created']['$date'] / 1000)
            
            app.logger.debug(f"Rune dictionary after date conversion: {rune_dict}")

            socketio.emit('rune_info_retrieved', rune_dict)
            return marshal(rune_dict, rune_model)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Internal server error")
            return {'message': f"Internal server error: {str(e)}"}, 500
        
# print(logging.basicConfig(level=logging.DEBUG))

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

# @api.route('/runes/make-psbt')
# class MakePSBTResource(Resource):
#     @api.doc(description='Create a PSBT for a rune')
#     @api.expect(make_psbt_model, validate=True)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             response = requests.post(URL + "/runes/make-psbt", json=args)
#             if response.status_code != 200:
#                 return jsonify({'error': 'Failed to create PSBT'}), response.status_code

#             psbt_data = response.json()
            
#             # Emit PSBT data to connected WebSocket clients
#             socketio.emit('psbt_created', {'data': psbt_data})

#             return jsonify(psbt_data)
#         except KeyError as e:
#             sentry_sdk.capture_exception(e)
#             return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
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
            app.logger.debug(f"Request args: {args}")
            response = requests.post(URL + "/runes/make-psbt", json=args)
            app.logger.debug(f"Response status code: {response.status_code}")
            app.logger.debug(f"Response content: {response.content}")

            if response.status_code != 200:
                app.logger.error(f"Failed to create PSBT: {response.status_code} - {response.text}")
                return jsonify({'error': 'Failed to create PSBT', 'details': response.text}), response.status_code

            psbt_data = response.json()
            app.logger.debug(f"PSBT data: {psbt_data}")

            # Emit PSBT data to connected WebSocket clients
            socketio.emit('psbt_created', {'data': psbt_data})

            return jsonify(psbt_data)
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Missing required field")
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except ValueError as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Error decoding JSON")
            return jsonify({'error': 'Error decoding JSON from response', 'message': str(e)}), 500
        except Exception as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Internal server error")
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

        
logging.basicConfig(level=logging.DEBUG)

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
            response = requests.post(URL + "/runes/make-listing", json=args)
            app.logger.debug(f"Response status code: {response.status_code}")
            app.logger.debug(f"Response content: {response.content}")

            if response.status_code != 200:
                return jsonify({'error': 'Failed to create listing'}), response.status_code

            listing_data = response.json()
            app.logger.debug(f"Listing data: {listing_data}")

            if 'error' in listing_data:
                return jsonify(listing_data), response.status_code
            
            # Emit listing data to connected WebSocket clients
            socketio.emit('listing_created', {'data': listing_data})

            return jsonify(listing_data)  # Return the JSON data directly
        except requests.exceptions.RequestException as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Request exception")
            return jsonify({'error': 'Request to external service failed', 'message': str(e)}), 500
        except ValueError as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Invalid JSON response")
            return jsonify({'error': 'Invalid JSON response from external service', 'message': str(e)}), 500
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("KeyError")
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            app.logger.exception("Internal server error")
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

# @api.route('/runes/make-listing')
# class MakeListingResource(Resource):
#     @api.doc(description='Create a listing for a rune')
#     @api.expect(make_listing_model, validate=True)
#     @cache.cached(timeout=300, query_string=True)
#     @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             response = requests.post(URL + "/runes/make-listing", json=args)
#             app.logger.debug(f"Response status code: {response.status_code}")
#             app.logger.debug(f"Response content: {response.content}")

#             if response.status_code != 200:
#                 return {'error': 'Failed to create listing'}, response.status_code

#             listing_data = response.json()
#             app.logger.debug(f"Listing data: {listing_data}")
            
#             # Emit listing data to connected WebSocket clients
#             socketio.emit('listing_created', {'data': listing_data})

#             return listing_data  # Return the JSON data directly
#         except requests.exceptions.RequestException as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("Request exception")
#             return {'error': 'Request to external service failed', 'message': str(e)}, 500
#         except ValueError as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("Invalid JSON response")
#             return {'error': 'Invalid JSON response from external service', 'message': str(e)}, 500
#         except KeyError as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("KeyError")
#             return {'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}, 400
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("Internal server error")
#             return {'error': 'Internal server error', 'message': str(e)}, 500
        
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
            listing_id = args.get('id')
            listing = RuneListing.objects(id=listing_id).first()

            # Log the query results
            if listing is None:
                app.logger.debug(f"Listing ID {listing_id} does not exist in the database.")
            else:
                app.logger.debug(f"Listing found: {listing.to_json()}")

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

            return completed_data  # Ensure this is JSON serializable
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

# @api.route('/runes/listings')
# class RuneListingsResource(Resource):
#     @api.doc(description='Get a list of rune listings with pagination and search')
#     @api.expect(pagination_params, validate=True)
#     @api.marshal_with(listing_response_model)
#     @cache.cached(timeout=300, query_string=True)
#     # @require_api_key
#     @limiter.limit("5 per minute")
#     def post(self):
#         try:
#             args = request.get_json()
#             page = args.get('page', 1)
#             limit = args.get('limit', 10)
#             search_query = args.get('search', '')
#             skip = (page - 1) * limit

#             # Enhanced search capabilities
#             query = Q(valid=True)
#             if 'rune' in args:
#                 query &= Q(rune__icontains=args['rune'])
#             if search_query:
#                 query &= (Q(rune__icontains=search_query) | Q(symbol__icontains=search_query) | Q(type__icontains=search_query))

#             app.logger.debug(f"Constructed Query: {query}")

#             posts = RuneListing.objects(query).skip(skip).limit(limit)
#             total_count = RuneListing.objects(query).count()

#             app.logger.debug(f"Fetched Posts: {posts}")
#             app.logger.debug(f"Total Count: {total_count}")

#             if posts is None or len(posts) == 0:
#                 app.logger.warning("No posts fetched from database.")
#             else:
#                 for post in posts:
#                     app.logger.debug(f"Fetched Post: {post.to_mongo()}")

#             listings = []
#             for listing in posts:
#                 try:
#                     app.logger.debug(f"Processing listing: {listing.to_mongo()}")

#                     # Handle the 'Created' field conversion
#                     if listing.Created:
#                         try:
#                             created_date = listing.Created.isoformat() if isinstance(listing.Created, datetime) else datetime.fromisoformat(str(listing.Created)).isoformat()
#                         except ValueError:
#                             created_date = None
#                     else:
#                         created_date = None

#                     listing_dict = {
#                         'id': str(listing.id),
#                         'type': listing.type if listing.type else '',
#                         'amount': listing.amount if listing.amount else 0,
#                         'price': listing.price if listing.price else 0,
#                         'rune': listing.rune if listing.rune else '',
#                         'symbol': listing.symbol if listing.symbol else '',
#                         'OrdinalAddress': listing.OrdinalAddress if listing.OrdinalAddress else '',
#                         'PaymentAddress': listing.PaymentAddress if listing.PaymentAddress else '',
#                         'CounterOffers': [str(offer) for offer in listing.CounterOffers] if listing.CounterOffers else [],
#                         'Completed': listing.Completed.isoformat() if listing.Completed else None,
#                         'spent': listing.spent if listing.spent else 0,
#                         'Created': created_date
#                     }
#                     app.logger.debug(f"Processed Listing: {listing_dict}")
#                     listings.append(listing_dict)
#                 except Exception as e:
#                     app.logger.exception(f"Error processing listing: {e}")
#                     sentry_sdk.capture_exception(e)

#             metadata = {
#                 "pageNumber": page,
#                 "perPage": limit,
#                 "pageCount": len(listings),
#                 "totalCount": total_count,
#                 "numOfPages": math.ceil(total_count / limit)
#             }

#             app.logger.debug(f"Listings: {listings}")
#             app.logger.debug(f"Metadata: {metadata}")

#             # Emit listings data to connected WebSocket clients
#             socketio.emit('listings_retrieved', {'listings': listings, 'metadata': metadata})

#             return {'listings': listings, 'metadata': metadata}
#         except KeyError as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("KeyError")
#             return {'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}, 400
#         except Exception as e:
#             sentry_sdk.capture_exception(e)
#             app.logger.exception("Internal server error")
#             return {'error': 'Internal server error', 'message': str(e)}, 500

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

            print(f"Constructed Query: {query}")

            posts = RuneListing.objects(query).skip(skip).limit(limit)
            total_count = RuneListing.objects(query).count()

            print(f"Fetched Posts: {posts}")
            print(f"Total Count: {total_count}")

            if posts is None or len(posts) == 0:
                print("No posts fetched from database.")
            else:
                for post in posts:
                    print(f"Fetched Post: {post.to_mongo()}")

            listings = []
            for listing in posts:
                try:
                    print(f"Processing listing: {listing.to_mongo()}")

                    # Handle the 'Created' field conversion
                    if listing.Created:
                        try:
                            created_date = listing.Created.isoformat() if isinstance(listing.Created, datetime) else datetime.fromisoformat(str(listing.Created)).isoformat()
                        except ValueError:
                            created_date = None
                    else:
                        created_date = None

                    listing_dict = {
                        'id': str(listing.id),
                        'type': listing.type if listing.type else '',
                        'amount': listing.amount if listing.amount else 0,
                        'price': listing.price if listing.price else 0,
                        'rune': listing.rune if listing.rune else '',
                        'symbol': listing.symbol if listing.symbol else '',
                        'OrdinalAddress': listing.OrdinalAddress if listing.OrdinalAddress else '',
                        'PaymentAddress': listing.PaymentAddress if listing.PaymentAddress else '',
                        'CounterOffers': [str(offer) for offer in listing.CounterOffers] if listing.CounterOffers else [],
                        'Completed': listing.Completed.isoformat() if listing.Completed else None,
                        'spent': listing.spent if listing.spent else 0,
                        'Created': created_date
                    }
                    print(f"Processed Listing: {listing_dict}")
                    listings.append(listing_dict)
                except Exception as e:
                    print(f"Error processing listing: {e}")
                    sentry_sdk.capture_exception(e)

            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(listings),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            print(f"Listings: {listings}")
            print(f"Metadata: {metadata}")

            # Emit listings data to connected WebSocket clients
            socketio.emit('listings_retrieved', {'listings': listings, 'metadata': metadata})

            return {'listings': listings, 'metadata': metadata}
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            print("KeyError")
            return {'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}, 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print("Internal server error")
            return {'error': 'Internal server error', 'message': str(e)}, 500
        
open_offers_pagination_params = api.model('OpenOffersPaginationParams', {
        'page': fields.Integer(description='Page number', required=True, example=1),
        'limit': fields.Integer(description='Number of items per page', required=True, example=10),
        'sort': fields.String(description='sort on basis of field', required=False, example='rune'),
        'OrdinalAddress': fields.String(description='Ordinal Address', required=False, example='tb1pl24s0tk7d8s3m0ph06tj85y2y8pa3xgx9xja8xzlnjy66g4q3hqq7juxxr')
})

history_pagination_params = api.model('HistoryPaginationParams', {
        'page': fields.Integer(description='Page number', required=True, example=1),
        'limit': fields.Integer(description='Number of items per page', required=True, example=10),
        'search': fields.String(description='Search' , required=False , example="RUNE•FOR•ALL" )
})


@api.route('/runes/open-offers')
class OpenRuneOffers(Resource):
    @api.doc(description='Retrieves open offers with pagination and sorting', security='apikey')
    @api.expect(open_offers_pagination_params, validate=True)
    @api.marshal_with(open_offers_response_model)
    @limiter.limit("5 per minute")
    # @cache.cached(timeout=300, key_prefix=custom_cache_key)
    # @require_api_key
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            filter_criteria = args.get('filter', {})
            sort_criteria = args.get('sort', None)

            
            
            addr = args.get('OrdinalAddress')

            query = Q(OrdinalAddress__icontains=addr) & Q(valid=True)
            skip = (page - 1) * limit

            print("query", query)
            offers = RuneListing.objects(query).skip(skip).limit(limit)
            print("offers", offers)
            # query = RuneListing.objects(valid=True, OrdinalAddress=addr)
            
            # Apply filter criteria
            # if filter_criteria:
            #     for key, value in filter_criteria.items():
            #         query = query.filter(**{key: value})
            
            # Apply sorting criteria
            # if sort_criteria:
            #     query = query.order_by(sort_criteria)
            
            total_count = offers.count()
            print("total_count", total_count)
            # offers = query.skip((page - 1) * limit).limit(limit)
            
            result = []
            for listing in offers:
                listing_dict = listing.to_mongo().to_dict()
                listing_dict['_id'] = str(listing_dict['_id'])
                listing_dict['Created'] = listing.Created.isoformat() if isinstance(listing.Created, datetime.datetime) else listing.Created
                listing_dict['Completed'] = listing.Completed.isoformat() if listing.Completed and isinstance(listing.Completed, datetime.datetime) else listing.Completed
                result.append(listing_dict)

            print("result", result)  
            
            metadata = {
                "pageNumber": page,
                "perPage": limit,
                "pageCount": len(result),
                "totalCount": total_count,
                "numOfPages": math.ceil(total_count / limit)
            }

            print("metadata", metadata)
            
            # Emit offers data to connected WebSocket clients
            socketio.emit('offers_retrieved', {'offers': result, 'metadata': metadata})

            return {'offers': result, 'metadata': metadata}
        
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500



@api.route('/runes/history')
class RuneHistoryResource(Resource):
    @api.doc(description='Get the history of rune sales with pagination and search')
    @api.expect(history_pagination_params, validate=True)
    @api.marshal_with(history_response_model)
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            skip = (page - 1) * limit

            print("page", page)
            print("limit", limit)
            print("search_query", search_query)

            # Initialize the query
            query = Q()

            # Apply search criteria
            if search_query:
                query &= (Q(rune__icontains=search_query) | Q(type__icontains=search_query))
            print("query", query)

            sales = RuneSale.objects(query).order_by('-time').skip(skip).limit(limit)
            print("sales", sales)
            total_count = RuneSale.objects(query).count()
            sales_list = []
            for sale in sales:
                sale_dict = sale.to_mongo().to_dict()
                sale_dict['_id'] = str(sale_dict['_id'])
                sale_dict['time'] = sale.time.isoformat() if isinstance(sale.time, datetime.datetime) else sale.time
                # Ensure no reference to 'listingID'
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
            print(f"KeyError: {str(e)}")
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(f"Exception: {str(e)}")
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
            response = requests.post(URL + "/runes/transfer", json=args)

            if response.status_code != 200:
                # Log the response content for debugging
                error_message = response.content.decode()
                app.logger.error(f"Error response from external server: {error_message}")
                return jsonify({'error': 'Failed to transfer rune', 'details': error_message}), response.status_code

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
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()

            required_fields = ['UserAddress', 'ServerAddress', 'Rune', 'TxIDs']
            missing_fields = [field for field in required_fields if field not in args or not args[field]]

            if missing_fields:
                return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

            txid = args['TxIDs'][0]

            if MintOrder.objects(tx_ids=txid).first():
                return jsonify({'error': 'This txid was already submitted as payment for an order.'}), 400

            # Include txid and id in the args
            args['txid'] = txid
            args['id'] = str(uuid.uuid4())  # Assuming id is a unique identifier for the request

            response = requests.post(URL + "/runes/mint", json=args)
            app.logger.debug(f'External service response status: {response.status_code}')
            app.logger.debug(f'External service response content: {response.content.decode("utf-8")}')

            if response.status_code != 200:
                try:
                    error_details = response.json()
                except ValueError:
                    error_details = response.text
                return jsonify({'error': 'Failed to mint rune', 'details': error_details}), response.status_code

            try:
                mint_data = response.json()
            except ValueError:
                app.logger.error(f'Invalid JSON response from external service: {response.content.decode("utf-8")}')
                return jsonify({'error': 'Invalid JSON response from external service'}), 500

            socketio.emit('rune_minted', {'data': mint_data})

            return jsonify(mint_data)
        except KeyError as e:
            app.logger.error(f'Missing required field: {str(e)}')
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': 400}), 400
        except requests.RequestException as e:
            app.logger.error(f'Error while making external request: {e}')
            return jsonify({'error': 'External request failed', 'message': str(e)}), 500
        except Exception as e:
            app.logger.error(f'Unexpected error: {e}')
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@api.route('/runes/mint-orders')
class MintOrdersResource(Resource):
    @api.doc(description='Get mint orders for a user with pagination and search')
    @api.expect(pagination_params, validate=True)
    @api.marshal_with(mint_orders_response_model)
    @cache.cached(timeout=300, query_string=True)
    # @require_api_key
    @limiter.limit("5 per minute")
    def post(self):
        try:
            args = request.get_json()
            page = args.get('page', 1)
            limit = args.get('limit', 10)
            search_query = args.get('search', '')
            userAddress = args.get('OrdinalAddress')

            logging.debug(f"UserAddress extracted: {userAddress}")

            if not userAddress:
                logging.error("UserAddress is missing from the request.")
                return jsonify({'error': 'UserAddress is required'}), 400
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

            data = Chart.objects(query).skip(skip).limit(limit).exclude('_id')
            tradeInfo = Chart.objects(rune=rune).exclude('_id').first()
            total_count = Chart.objects(query).count()
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

total_model = api.model('Total', {
    'total': fields.List(fields.Raw, description='Total count'),
    'metadata': fields.Nested(metadata_model)
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
    'metadata': fields.Nested(metadata_model)
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
            listing = RuneListing.objects(id=args.get('id')).first()
            if listing is None:
                return jsonify({'error': "That listing does not exist.", 'code': error_codes['offer_not_exist']}), 404
            if not listing.valid:
                return jsonify({'error': "This listing is no longer valid.", 'code': error_codes['offer_is_invalid']}), 400
            
            # Emit counteroffer placement to connected WebSocket clients
            socketio.emit('counteroffer_placed', {'listing_id': args['id'], 'price': args['price'], 'ordinal_address': args['OrdinalAddress']})

            return requests.post(URL + "/runes/place-counteroffer", json=args).json()
        except KeyError as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': f'Missing required field: {str(e)}', 'code': error_codes['missing_info']}), 400
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

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
            listing = RuneListing.objects(id=args.get('id')).first()
            if listing is None:
                return jsonify({'error': "That listing does not exist.", 'code': error_codes['offer_not_exist']}), 404
            if not listing.valid:
                return jsonify({'error': "This listing is no longer valid.", 'code': error_codes['offer_is_invalid']}), 400
            
            # Emit counteroffer completion to connected WebSocket clients
            socketio.emit('counteroffer_completed', {'listing_id': args['id'], 'txid': args['txid']})

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
