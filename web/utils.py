import random
from web.models import Bill

def generate_unique_loyalty_code():
    from web import db  # Import inside to avoid circular import
    while True:
        code = str(random.randint(1000, 9999))
        if not Bill.query.filter_by(loyalty_code=code).first():
            return code
