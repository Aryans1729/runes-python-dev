# Rune API

This project provides a RESTful API for managing runes. The following features have been implemented:

## **Key Components:-**
**Flask**: The micro web framework used to build the API.
**MongoEngine**: A Document-Object Mapper (like an ORM for SQL) for MongoDB to simplify database interactions.
**Redis**: An in-memory data structure store used for caching.
**Flask-Caching**: A Flask extension to integrate caching mechanisms like Redis.
**Sentry**: Used for error tracking and monitoring.
**Flask-Limiter**: Used to rate-limit the API requests.
**Flask-RESTX**: An extension for Flask that adds support for creating REST APIs with integrated Swagger documentation.

1. **Conversion from `pymongo` to `mongoengine`**: 
   - All database operations now use `mongoengine`, an Object-Document Mapper (ODM) for MongoDB, instead of raw `pymongo` queries.
   - **Original PyMongo Implementation**
        - The original implementation used PyMongo to directly interact with MongoDB. An example route might have looked like this:
        
        ```python
        
            @app.route('/runes/listings', methods=['POST'])
            def getRuneListings():
            args = request.get_json()
            rune = args.get('rune')
            listings = pymongo.db.runelistings.find({'valid': True, 'rune': rune})
            #process listings
        ```
   - **MongoEngine Implementation**
        - MongoEngine provides a more `Pythonic` way to interact with MongoDB using classes and objects. Here's how the same     functionality is implemented using MongoEngine:
        1. **Define MongoEngine Models:**

        ```python
        from mongoengine import Document, StringField, IntField, BooleanField

        class RuneListing(Document):
            rune = StringField(required=True)
            valid = BooleanField(default=True)
            amount = IntField()
            price = IntField()
            type = StringField()
            OrdinalAddress = StringField()
            PaymentAddress = StringField()
            CounterOffers = ListField(StringField())  # Assuming CounterOffers are strings for simplicity
        ```
        2. **Updated Route:**

        ```python
            @app.route('/runes/listings', methods=['POST'])
            @cache.cached(timeout=300, query_string=True)
            def getRuneListings():
                args = request.get_json()
                rune = args.get('rune')
                posts = RuneListing.objects(valid=True, rune=rune)
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
                        'CounterOffers': listing.CounterOffers
                    }
                    listings.append(listing_dict)
                return jsonify(listings)

        ```

2. **Access Limit to API**:
   - Rate limiting has been implemented using `flask-limiter`.
   - Each user is limited to 5 requests per minute to the `/runes` endpoint.
   - Exceeding this limit will return a 429 status code with a "Too Many Requests" error.

3. **Pagination and Search**:
   - The `/runes` endpoint supports pagination.
   - Clients can specify the `page` and `limit` parameters to paginate results.
   - Clients can also use the `search` parameter to filter results based on the `SpacedRune` field.

4. **API Key Authentication**:
   - API keys are used to authenticate users.
   - Requests to the `/runes` endpoint must include a valid API key.

5. **Redis Implementation**:
   - **Introduction to Caching with Redis*:-**
    Redis is used to cache frequently accessed data, reducing the load on the MongoDB database and improving API response times. Flask-Caching is the extension used to integrate Redis with Flask.
    1. Configuration[^1]
        Install Redis and Flask-Caching:

        ```python
        pip install redis Flask-Caching
        ```
    2. Configure Flask-Caching with Redis:[^2]
        ```python 
        app.config['CACHE_TYPE'] = 'RedisCache'
        app.config['CACHE_REDIS_HOST'] = 'localhost'
        app.config['CACHE_REDIS_PORT'] = 6380
        app.config['CACHE_REDIS_DB'] = 0
        app.config['CACHE_REDIS_URL'] = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Cache timeout in seconds
        ```
    - **Caching API Responses:-**
        - To cache the responses of API endpoints, use the @cache.cached decorator. This caches the response for the specified timeout period. For example:

        ```python 
        @app.route('/runes/listings', methods=['POST'])
        @cache.cached(timeout=300, query_string=True)
        def getRuneListings():
        # Function implementation
        ```
        
6. **Improved Error Handling**:
   - Comprehensive error handling has been implemented to ensure clear and consistent error messages.
   - Errors are returned with appropriate status codes and messages.

7. **Swagger Documentation**:
   - Swagger has been implemented for API documentation.
   - The API documentation can be accessed at `/swagger-ui`.
   - curl "http://localhost:5000/docs" in your browser to access swagger.


## Implementation Summary
1. Conversion to MongoEngine:
    - Define MongoEngine document models.
    - Replace PyMongo queries with MongoEngine's ORM-like query syntax.
    - Update all routes to utilize MongoEngine models for database interactions.
2. Redis Caching:
    - Configure Flask-Caching with Redis.
    - Apply caching to API routes using the @cache.cached decorator to improve performance.


## Endpoints

### `/runes` [POST]

#### Description
Get a list of runes with pagination and search capabilities.

#### Parameters

- `page` (int, optional): The page number to retrieve. Default is 1.
- `limit` (int, optional): The number of items per page. Default is 10.
- `search` (string, optional): A search query to filter runes by the `SpacedRune` field.

#### Example Request

```bash
curl -X POST "http://localhost:5000/runes" \
    -H "Content-Type: application/json" \
    -H "x-api-key: YOUR_API_KEY" \
    -d '{
        "page": 1,
        "limit": 10,
        "search": "SCAM"
    }'
