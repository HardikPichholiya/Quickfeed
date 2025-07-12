from web import db
from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy.orm import validates


class BaseUser(UserMixin, db.Model):
    """Base class for User and Shopkeeper with common fields."""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate and normalize email"""
        if email:
            return email.strip().lower()
        return email
    
    @validates('first_name', 'last_name')
    def validate_names(self, key, name):
        """Validate and normalize names"""
        if name:
            return name.strip().title()
        return name
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {self.email}>'


class User(BaseUser):
    """Regular customer users who can give feedback."""
    __tablename__ = 'users'  
    points = db.Column(db.Integer, default=0)
    def get_feedback_count(self):
        """Get total number of feedbacks given by this user"""
        return len(self.feedbacks)
    
    def get_recent_feedback(self, limit=5):
        """Get recent feedback given by this user"""
        return sorted(self.feedbacks, key=lambda x: x.created_at, reverse=True)[:limit]


class Shopkeeper(BaseUser):
    """Shopkeepers who own shops and receive feedback."""
    __tablename__ = 'shopkeepers'  # Changed from 'shopkeeper' to 'shopkeepers'
    
    shopname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Add relationship to feedback with proper foreign key handling
    received_feedbacks = db.relationship('Feedback',
                                       foreign_keys='Feedback.shopkeeper_id',
                                       backref='shopkeeper',
                                       lazy='dynamic',
                                       cascade='all, delete-orphan')
    
    @validates('username')
    def validate_username(self, key, username):
        """Validate and normalize username"""
        if username:
            return username.strip().lower()
        return username
    
    @validates('shopname')
    def validate_shopname(self, key, shopname):
        """Validate and normalize shop name"""
        if shopname:
            return shopname.strip()
        return shopname
    
    @property
    def average_rating(self):
        """Calculate average rating for this shopkeeper."""
        feedbacks = self.received_feedbacks.all()
        if not feedbacks:
            return 0.0
        
        total_rating = sum(feedback.rating for feedback in feedbacks)
        return round(total_rating / len(feedbacks), 2)
    
    @property
    def total_feedbacks(self):
        """Get total number of feedbacks."""
        return self.received_feedbacks.count()
    
    @property
    def rating_distribution(self):
        """Get distribution of ratings (1-5 stars)."""
        feedbacks = self.received_feedbacks.all()
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for feedback in feedbacks:
            if 1 <= feedback.rating <= 5:
                distribution[feedback.rating] += 1
        
        return distribution
    
    @property
    def satisfaction_rate(self):
        """Calculate satisfaction rate (4-5 stars)"""
        feedbacks = self.received_feedbacks.all()
        if not feedbacks:
            return 0.0
        
        satisfied = sum(1 for feedback in feedbacks if feedback.rating >= 4)
        return round((satisfied / len(feedbacks)) * 100, 1)
    
    def get_recent_feedback(self, limit=10):
        """Get recent feedback for this shopkeeper"""
        return self.received_feedbacks.order_by(Feedback.created_at.desc()).limit(limit).all()


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    shopkeeper = db.relationship('Shopkeeper', backref=db.backref('items', lazy=True))

# In models.py, update the Bill class
class Bill(db.Model):
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    customer_email = db.Column(db.String(120), nullable=True)  # Add this line
    loyalty_code = db.Column(db.String(4), unique=True, nullable=True)
    loyalty_used = db.Column(db.Boolean, default=False)
    loyalty_points_earned = db.Column(db.Integer, default=0)
    shopkeeper = db.relationship('Shopkeeper', backref=db.backref('bills', lazy=True))


class BillItem(db.Model):
    __tablename__ = 'bill_items'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)

    bill = db.relationship('Bill', backref=db.backref('bill_items', lazy=True))
    item = db.relationship('Item', backref=db.backref('bill_items', lazy=True))

class Feedback(db.Model):
    """Feedback given by users to shopkeepers."""
    __tablename__ = 'feedbacks'  # Changed from 'feedback' to 'feedbacks'
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    shopkeeper_id = db.Column(db.Integer, 
                             db.ForeignKey('shopkeepers.id', ondelete='CASCADE'), 
                             nullable=False)
    
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_user = db.relationship('User', 
                                  foreign_keys=[customer_email],
                                  primaryjoin='Feedback.customer_email == User.email',
                                  backref='feedbacks',
                                  lazy=True)
    # Add database constraints
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='rating_range'),
        db.CheckConstraint('LENGTH(title) >= 3', name='title_min_length'),
        db.CheckConstraint('LENGTH(content) >= 10', name='content_min_length'),
    )
    @property
    def customer_display_name(self):
        """Returns customer name or 'Anonymous'"""
        return self.customer_name or "Anonymous"

    @property
    def customer_display_email(self):
        """Returns email or 'Not provided'"""
        return self.customer_email or "Not provided"

    @validates('rating')
    def validate_rating(self, key, rating):
        """Validate rating is between 1-5"""
        if rating is not None:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError("Rating must be between 1 and 5")
        return rating
    
    @validates('title')
    def validate_title(self, key, title):
        """Validate and clean title"""
        if title:
            title = title.strip()
            if len(title) < 3:
                raise ValueError("Title must be at least 3 characters long")
            if len(title) > 200:
                raise ValueError("Title cannot exceed 200 characters")
        return title
    
    @validates('content')
    def validate_content(self, key, content):
        """Validate and clean content"""
        if content:
            content = content.strip()
            if len(content) < 10:
                raise ValueError("Content must be at least 10 characters long")
            if len(content) > 5000:
                raise ValueError("Content cannot exceed 5000 characters")
        return content
    
    @validates('customer_name')
    def validate_customer_name(self, key, customer_name):
        """Validate and clean customer name"""
        if customer_name:
            customer_name = customer_name.strip()
            if len(customer_name) < 2:
                raise ValueError("Customer name must be at least 2 characters long")
        return customer_name
    
    @validates('customer_email')
    def validate_customer_email(self, key, customer_email):
        """Validate and clean customer email"""
        if customer_email:
            customer_email = customer_email.strip().lower()
            # Basic email validation
            if '@' not in customer_email or '.' not in customer_email:
                raise ValueError("Invalid email format")
        return customer_email
    
    def __repr__(self):
        return f'<Feedback {self.title}>'
    
    @property
    def time_ago(self):
        """Get human-readable time ago string with proper timezone handling."""
        now = datetime.now(timezone.utc)
        
        # Ensure created_at is timezone-aware
        if self.created_at.tzinfo is None:
            created_at_utc = self.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = self.created_at
        
        diff = now - created_at_utc
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    @property
    def rating_stars(self):
        """Get star representation of rating"""
        return '⭐' * self.rating
    
    @property
    def rating_text(self):
        """Get text representation of rating"""
        rating_map = {
            1: 'Terrible',
            2: 'Poor',
            3: 'Average',
            4: 'Good',
            5: 'Excellent'
        }
        return rating_map.get(self.rating, 'Unknown')
    
    def to_dict(self):
        """Convert feedback to dictionary for JSON responses"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'rating': self.rating,
            'rating_stars': self.rating_stars,
            'rating_text': self.rating_text,
            'customer_name': self.customer_display_name,
            'customer_email': self.customer_display_email,
            'created_at': self.created_at.isoformat(),
            'time_ago': self.time_ago,
            'is_anonymous': self.is_anonymous,
            'shopkeeper_id': self.shopkeeper_id
        }
    
    @classmethod
    def create_feedback(cls, **kwargs):
        """Factory method to create feedback with validation."""
        try:
            # Extract and validate required fields
            title = kwargs.get('title', '').strip()
            content = kwargs.get('content', '').strip()
            rating = kwargs.get('rating')
            shopkeeper_id = kwargs.get('shopkeeper_id')
            
            # Validate required fields
            if not title or len(title) < 3:
                raise ValueError("Title is required and must be at least 3 characters long")
            
            if not content or len(content) < 10:
                raise ValueError("Content is required and must be at least 10 characters long")
            
            if not rating or not (1 <= int(rating) <= 5):
                raise ValueError("Rating must be between 1 and 5")
            
            if not shopkeeper_id:
                raise ValueError("Shopkeeper ID is required")
            
            # Check if shopkeeper exists
            shopkeeper = Shopkeeper.query.get(shopkeeper_id)
            if not shopkeeper:
                raise ValueError("Shopkeeper not found")
            
            if not shopkeeper.is_active:
                raise ValueError("Shopkeeper account is inactive")
            
            # Create feedback instance
            feedback = cls(
                title=title,
                content=content,
                rating=int(rating),
                shopkeeper_id=shopkeeper_id,
                customer_name=kwargs.get('customer_name', '').strip() if kwargs.get('customer_name') else None,
                customer_email=kwargs.get('customer_email', '').strip().lower() if kwargs.get('customer_email') else None
            )
            
            return feedback
            
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error creating feedback: {str(e)}")
    
    @classmethod
    def get_by_shopkeeper(cls, shopkeeper_id, limit=None):
        """Get feedback for a specific shopkeeper"""
        query = cls.query.filter_by(shopkeeper_id=shopkeeper_id).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_recent_feedback(cls, days=30, limit=None):
        """Get recent feedback within specified days"""
        cutoff_date = datetime.now(timezone.utc) - timezone(days=days)
        query = cls.query.filter(cls.created_at >= cutoff_date).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()


# Add indexes for better performance
def create_indexes():
    """Create database indexes for better performance"""
    try:
        # Create indexes if they don't exist
        db.engine.execute('CREATE INDEX IF NOT EXISTS idx_feedback_shopkeeper_created ON feedbacks(shopkeeper_id, created_at DESC);')
        db.engine.execute('CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedbacks(rating);')
        db.engine.execute('CREATE INDEX IF NOT EXISTS idx_shopkeeper_username ON shopkeepers(username);')
        db.engine.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);')
        db.engine.execute('CREATE INDEX IF NOT EXISTS idx_shopkeeper_email ON shopkeepers(email);')
        
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {e}")