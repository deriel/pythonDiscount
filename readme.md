# Simple Discount microservice

## Requirements
- Python 3.9
- Pipenv

## Getting it up and running
    pipenv install
    pipenv run hug -f api.py

## Documentation
After the environment is setup it can be found at http://localhost:8000/

## Getting a JWT token for testing out the API:
    TOKEN=$(pipenv run python3 api.py)
Will give you a token for the default user for the default client, add user id to test claiming codes.
    curl \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    --request POST \
    --data '{"count":5,"name":"My pretty little discount"}' \
    http://localhost:8000/discount | jq


## Claiming a discount:
    curl \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    --request POST \
    --data '{"discount":"DISCOUNT_ID_FROM_ABOVE", "store": "A STORE_ID"}' \
    http://localhost:8000/discount/claim -v | jq