from mongoengine import Document, StringField, IntField, FloatField, BooleanField, ListField, DateTimeField, DictField
import datetime

# class APIKey(Document):
#     key = StringField(required=True, unique=True)
#     created_at = DateTimeField(default=datetime.datetime.utcnow)

class APIKey(Document):
    key = StringField(required=True, unique=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

class Chart(Document):
    tick = StringField(required=True)
    time = DateTimeField(default=datetime.datetime.utcnow)
    open = IntField()
    volume = IntField()
    high = IntField()
    low = IntField()
    close = IntField()

class Counts(Document):
    mints = IntField()
    trades = IntField()
    transfers = IntField()

# class MintOrder(Document):
#     UserAddress = StringField(required=True, db_field="UserAddress")
#     ServerAddress = StringField(required=True, db_field="ServerAddress")
#     TotalFee = IntField(db_field="TotalFee")
#     Repeats = IntField(db_field="Repeats")
#     Rune = StringField(required=True,db_field="Rune")
#     Destination = StringField(db_field="Destination")
#     FeeRate = IntField(db_field="FeeRate")
#     Remaining = IntField(db_field="Remaining")
#     Paid = BooleanField(db_field="Paid")
#     Completed = BooleanField(db_field="Completed")
#     TimeCreated = DateTimeField(default=datetime.datetime.utcnow,db_field="TimeCreated")
#     TxIDs = ListField(StringField(),db_field="TxIDs")
#     TimeCompleted = DateTimeField(db_field="TimeCompleted")
#     TimeUpdated = DateTimeField(default=datetime.datetime.utcnow,db_field="TimeUpdated")
#     meta = {'collection': 'mintorders'}

# class MintOrder(Document):
#     user_address = StringField(required=True, description='UserAddress')
#     server_address = StringField(required=True, description='ServerAddress')
#     total_fee = IntField(description='TotalFee')
#     repeats = IntField(description='Repeats')
#     rune = StringField(required=True, description='Rune')
#     destination = StringField(description='Destination')
#     fee_rate = IntField(description='FeeRate')
#     remaining = IntField(description='Remaining')
#     paid = BooleanField(description='Paid')
#     completed = BooleanField(description='Completed')
#     time_created = DateTimeField(description='TimeCreated')
#     tx_ids = ListField(StringField(), required=True, description='TxIDs')
#     time_completed = DateTimeField(description='TimeCompleted')
#     time_updated = DateTimeField(description='TimeUpdated')
#     meta = {'collection': 'mintorders'}

class MintOrder(Document):
    user_address = StringField(required=True)
    server_address = StringField(required=True)
    total_fee = IntField()
    repeats = IntField()
    rune = StringField(required=True)
    destination = StringField()
    fee_rate = IntField()
    remaining = IntField()
    paid = BooleanField()
    completed = BooleanField()
    time_created = DateTimeField(default=datetime.datetime.utcnow)
    tx_ids = ListField(StringField(), required=True)
    time_completed = DateTimeField()
    time_updated = DateTimeField()
    meta = {'collection': 'mintorders'}

class Points(Document):
    address = StringField(required=True)
    points = IntField()
    meta = {
        'collection': 'points',
        'indexes': [
            'address',
        ]
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


class RuneName(Document):
    names = ListField(StringField())

# class RuneListing(Document):
#     PaymentAddress = StringField(required=True,db_field = "PaymentAddress")
#     OrdinalAddress = StringField(required=True , db_field = "OrdinalAddress")
#     rune = StringField(required=True, db_field = "rune")
#     amount = IntField(db_field = "amount")
#     price = IntField(db_field = "price")
#     type = StringField(db_field = "type")
#     psbt = StringField(db_field = "psbt")
#     wallet = StringField(db_field = "wallet")
#     valid = BooleanField(db_field = "valid")
#     CounterOffers = ListField(DictField(db_field = "CounterOffers"))
#     Completed = DateTimeField(db_field = "Completed")
#     spent = FloatField(db_field = "spent")

#     meta = {'collection': 'runelistings'}


class RuneListing(Document):
    PaymentAddress = StringField(required=True, db_field="PaymentAddress")
    OrdinalAddress = StringField(required=True, db_field="OrdinalAddress")
    rune = StringField(required=True, db_field="rune")
    amount = IntField(db_field="amount")
    price = IntField(db_field="price")
    type = StringField(db_field="type")
    psbt = StringField(db_field="psbt")
    wallet = StringField(db_field="wallet")
    valid = BooleanField(db_field="valid")
    CounterOffers = ListField(DictField(), db_field="CounterOffers")
    Completed = DateTimeField(db_field="Completed")
    spent = FloatField(db_field="spent")
    symbol = StringField(db_field="symbol")  # Add symbol field
    Created = DateTimeField(db_field="Created")  # Add Created field
    
    meta = {'collection': 'runelistings'}

class RuneSale(Document):
    txid = StringField(required=True)
    TakerPaymentAddress = StringField(required=True)
    TakerOrdinalAddress = StringField(required=True)
    MakerPaymentAddress = StringField(required=True)
    MakerOrdinalAddress = StringField(required=True)
    MakerWallet = StringField()
    amount = IntField()
    price = IntField()
    rune = StringField(required=True)
    listingID = StringField()
    type = StringField()
    time = DateTimeField(default=datetime.datetime.utcnow)

class TradingInfo(Document):
    Rune = StringField(required=True)
    Supply = IntField()
    Symbol = StringField()
    Divisibility = IntField()
    Mintable = BooleanField()


