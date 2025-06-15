# from web import create_app, db
# from web.models import User

# # Create app instance
# app = create_app()

# # Run inside application context
# with app.app_context():
#     users = User.query.all()
#     for user in users:
#         print(f"{user.id} - {user.full_name} - {user.email}")

from web import create_app, db
from web.models import User, Feedback

app = create_app()

with app.app_context():
    # Delete data from each table
    db.session.query(Feedback).delete()
    db.session.query(User).delete()
    
    db.session.commit()
    print("All table data cleared successfully.")
