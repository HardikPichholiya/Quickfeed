from web import create_app, db
from web.models import Feedback  # 👈 Add your other models here (like User, Report, etc.)

app = create_app()

with app.app_context():
    db.create_all()

    # 🔥 TEMPORARY: Clear all data from tables
    db.session.query(Feedback).delete()  # 👈 Add more models as needed
    db.session.commit()
    print("✅ Database cleared.")

if __name__ == '__main__':
    app.run(debug=True)
