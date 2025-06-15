from web import create_app, db

app = create_app()

# Create tables within app context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)