from mongoengine import Document, StringField, DateTimeField, IntField, FloatField, BooleanField, ListField, BooleanField, EmbeddedDocument, EmbeddedDocumentField

# class APIKey(Document):
#     key = StringField(required=True, unique=True)
#     user = StringField(required=True)
#     created_at = DateTimeField(default=datetime.datetime.utcnow)

# class Point(Document):
#     meta = {'collection': 'points'}
#     address = StringField(required=True)
#     points = IntField(required=True)

#     meta = {
#         'collection': 'points'
#     }

class Points(Document):
    address = StringField(required=True)
    points = IntField(required=True)

    meta = {
        'collection': 'points',
        'indexes': [
            'address',
        ]
    }


class ChartData(Document):
    tick = StringField(required=True)
    time = DateTimeField(required=True)
    open = IntField(required=True)
    volume = IntField(required=True)
    high = IntField(required=True)
    low = IntField(required=True)
    close = IntField(required=True)

    meta = {
        'collection': 'chart'
    }

class Counts(Document):
    mints = IntField(required=True)
    trades = IntField(required=True)
    transfers = IntField(required=True)

    meta = {
        'collection': 'counts'
    }

class MintOrder(Document):
    UserAddress = StringField(required=True)
    ServerAddress = StringField(required=True)
    TotalFee = IntField(required=True)
    Repeats = IntField(required=True)
    Rune = StringField(required=True)
    Destination = StringField(required=True)
    FeeRate = IntField(required=True)
    Remaining = IntField(required=True)
    Paid = BooleanField(default=False)
    Completed = BooleanField(default=False)
    TxIDs = ListField(StringField())
    TimeCompleted = DateTimeField(db_field="TimeCompleted")
    TimeUpdated = DateTimeField(db_field="TimeUpdated")

    meta = {
        'collection': 'runesales'
    }


class Rune(Document):
    SpacedRune = StringField(required=True, db_field="SpacedRune")
    Created = DateTimeField(db_field="Created")
    Divisibility = IntField(db_field="Divisibility")
    EtchTx = StringField(db_field="EtchTx")
    LimitPerMint = IntField(db_field="LimitPerMint")
    MaxMintNumber = IntField(db_field="MaxMintNumber")
    MintEndAfter = DateTimeField(db_field="MintEndAfter")
    MintEndBlock = IntField(db_field="MintEndBlock")
    MintStartBlock = IntField(db_field="MintStartBlock")
    Minted = IntField(db_field="Minted")
    Premine = IntField(db_field="Premine")
    Progress = FloatField(db_field="Progress")
    RuneID = StringField(db_field="RuneID")
    Supply = IntField(db_field="Supply")
    Symbol = StringField(db_field="Symbol")
    Mintable = BooleanField(db_field="Mintable")


    meta = {'collection': 'runeInfo'}


class CounterOffer(EmbeddedDocument):
    OrdinalAddress = StringField()
    PaymentAddress = StringField()
    wallet = StringField()
    price = FloatField()
    psbt = StringField()

class RuneSale(Document):
    txid = StringField(required=True)
    TakerPaymentAddress = StringField(required=True)
    TakerOrdinalAddress = StringField()
    TakerWallet = StringField(required=True)
    MakerPaymentAddress = StringField(required=True)
    MakerOrdinalAddress = StringField(required=True)
    MakerWallet = StringField(required=True)
    amount = FloatField(required=True)
    price = FloatField(required=True)
    rune = StringField(required=True)
    type = StringField(required=True)
    time = DateTimeField(required=True)

    meta = {
        'collection': 'runesales'
    }


class RuneListing(Document):
    PaymentAddress = StringField()
    OrdinalAddress = StringField()
    rune = StringField()
    amount = IntField()
    price = IntField()
    type = StringField()
    psbt = StringField()
    wallet = StringField()
    valid = BooleanField()
    symbol = StringField()
    Created = DateTimeField()
    CounterOffers = ListField(EmbeddedDocumentField(CounterOffer))
    Completed = DateTimeField()
    spent     = BooleanField()

    # meta = {'collection': 'runelistings'}

    meta = {
        'indexes': [
            'rune',
            'symbol',
            'OrdinalAddress',
            'PaymentAddress'
        ]
    }

class TradingInfo(Document):
    Rune = StringField(required=True)
    Supply = IntField(required=True)
    Symbol = StringField(required=True)
    Divisibility = IntField(required=True)
    Mintable = BooleanField(required=True)

    meta = {
        'collection': 'tradingInfo'
    }