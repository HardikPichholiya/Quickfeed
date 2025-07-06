from web import create_app, db
from web.models import Feedback 

app = create_app()

with app.app_context():
    #added on 29
    from web.models import db
    #db.drop_all()

    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)


#this is comment