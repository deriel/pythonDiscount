import hug
import jwt
import json
import uuid
from datetime import datetime, timedelta
from falcon import HTTP_404, HTTP_409
from marshmallow import fields
from marshmallow.validate import Range
from db import PersistentDict


# Authorization boilerplate, should be config/env variables:

JWT_OPTIONS = {
    'verify_signature': True,
    'verify_exp': True,
    'verify_nbf': False,
    'verify_iat': False,
    'verify_aud': True,
    'verify_iss': True,
    'require_exp': True,
    'require_iat': False,
    'require_nbf': False
}
SECRET_KEY = 'some-super-secret'
JWT_ISSUER = 'some-issuer'
JWT_AUDIENCE = 'some-audience'
JWT_OPTIONS_ALGORITHM = 'HS256'


def jwt_token_verify(auth_header):
    try:
        parts = auth_header.split()

        if parts[0].lower() != 'bearer' or len(parts) == 1 or len(
                parts) > 2:
            return false

        return jwt.decode(
            parts[1],
            SECRET_KEY,
            algorithms=(JWT_OPTIONS_ALGORITHM,),
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options=JWT_OPTIONS
        )
    except jwt.DecodeError:
        return False


token_key_authentication = hug.authentication.token(jwt_token_verify)


@hug.cli()
def generate_jwt_token(
    user: hug.types.uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'user.test')),
    brand: hug.types.uuid = str(uuid.uuid3(
        uuid.NAMESPACE_DNS, 'brand.test')),
    exp: datetime = None
):
    if exp is None:
        exp = datetime.utcnow() + timedelta(seconds=3600)
    payload = {
        'aud': JWT_AUDIENCE,
        'exp': exp,
        'iss': JWT_ISSUER,
        'uid': str(user),
        'bid': str(brand),
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=JWT_OPTIONS_ALGORITHM
    )


# Models:

class Discount:
    id: hug.types.uuid
    name: str
    brand: hug.types.uuid
    codes: list

    def __init__(self, id, name, brand, count):
        self.id = id
        self.name = name
        self.brand = brand
        self.codes = [Code(uuid.uuid4()) for i in range(count)]

    def __native_types__(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'codes': len(self.codes),
            'claimed': len([c for c in self.codes if c.claimed_at != None])
        }


class Code:
    id: hug.types.uuid
    claimed_by: hug.types.uuid = None
    claimed_at: datetime = None
    claimed_in: hug.types.uuid = None

    def __init__(self, id):
        self.id = id

    def __native_types__(self):
        return {
            'id': self.id,
            'claimed_by': self.claimed_by,
            'claimed_at': self.claimed_at,
            'claimed_in': self.claimed_in,
        }


# API Routes:

@hug.post('/discount', requires=token_key_authentication)
def create(count: fields.Int(validate=Range(min=1)), name: str, user: hug.directives.user):
    discount = Discount(
        id=uuid.uuid4(),
        name=name,
        brand=user['bid'],
        count=count,
    )
    with PersistentDict('./discounts.db', 'c') as db:
        db[discount.id] = discount

    return discount


@hug.get('/discounts')
def list(brand: hug.types.uuid):
    with PersistentDict('./discounts.db', 'r') as db:
        # str cast due to hug.types.uuid not having .int for comparisons with uuid package uuids...
        return [d for (k, d) in db.items() if str(d.brand) == str(brand)]


@hug.get('/codes', requires=token_key_authentication)
def my_claimed_codes(user: hug.directives.user):
    with PersistentDict('./discounts.db', 'r') as db:
        # str cast due to hug.directives.user not having .int for comparisons with uuid package uuids
        return [c for c in d.codes for (k, d) in db.items() if str(c.claimed_by) == str(user['uid'])]


@hug.post('/discount/claim', requires=token_key_authentication)
def claim(
    discount: hug.types.uuid,
    store: hug.types.uuid,
    user: hug.directives.user,
    response
):
    user_id = uuid.UUID(user['uid'])
    with PersistentDict('./discounts.db', 'c') as db:
        if discount in db:
            for c in db[discount].codes:
                if c.claimed_by == user_id:
                    response.status = HTTP_409
                    return {'errors': {'discount': "You've already claimed this discount"}}
                if c.claimed_by == None:
                    c.claimed_by = user_id
                    c.claimed_at = datetime.utcnow()
                    # No validation is done on store existence atm, that would need to be verified against stores service:
                    c.claimed_in = store

                    # Here is where dispatch to something like https://github.com/uber/cadence or similar nice integration-server would happen to let other microservices know that a code has been claimed and actions need to be taken (Notify brand via email, issue webhook requests to store so that they can create it in their system etc)

                    return c.id
    response.status = HTTP_404
    return {'errors': {'discount': 'Not found'}}


if __name__ == '__main__':
    generate_jwt_token.interface.cli()
