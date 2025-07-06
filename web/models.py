from web import db
from datetime import datetime
from flask_login import UserMixin


#added on 29 

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeeper.id'), nullable=False)

    shopkeeper = db.relationship('Shopkeeper', backref='items')
    feedbacks = db.relationship('Feedback', back_populates='item', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name}>'
#

class Shopkeeper(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    shopname = db.Column(db.String(100), nullable=True)  # For shopkeepers
    username = db.Column(db.String(50), unique=True, nullable=True)  # For shopkeepers
    def __repr__(self):
        return f'<Shopkeeper {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Made nullable for anonymous feedback
    customer_name = db.Column(db.String(100), nullable=True)  # For anonymous feedback
    customer_email = db.Column(db.String(120), nullable=True)  # Optional for anonymous feedback
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)  # Foreign key to Item###
    item=relationship('Item', back_populates='feedbacks')##
    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    #shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeeper.id'))




    ##
class ItemFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
