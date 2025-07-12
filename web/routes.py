from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify, session, abort
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import  func
from datetime import datetime, timedelta
import qrcode
import io
import base64
from web import db, socketio
from web.models import User, Feedback, Shopkeeper , Item, Bill
from web.forms import FeedbackForm, PublicFeedbackForm

main = Blueprint('main', __name__)
customer = Blueprint('customer', __name__)

class StatisticsService:
    """Service for calculating shopkeeper statistics"""
    
    @staticmethod
    def get_shopkeeper_stats(shopkeeper_id):
        """Get comprehensive statistics for a shopkeeper"""
        try:
            shopkeeper = Shopkeeper.query.get(shopkeeper_id)
            if not shopkeeper:
                return None
            
            # Get all feedback for this shopkeeper
            feedbacks = Feedback.query.filter_by(shopkeeper_id=shopkeeper_id).all()
            
            if not feedbacks:
                return {
                    'total_feedbacks': 0,
                    'average_rating': 0,
                    'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                    'recent_feedbacks': [],
                    'satisfaction_rate': 0
                }
            
            # Calculate statistics
            total_feedbacks = len(feedbacks)
            total_rating = sum(f.rating for f in feedbacks)
            average_rating = total_rating / total_feedbacks if total_feedbacks > 0 else 0
            
            # Rating distribution
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for feedback in feedbacks:
                if 1 <= feedback.rating <= 5:  # Validate rating range
                    rating_distribution[feedback.rating] += 1
            
            # Calculate satisfaction rate (4-5 stars)
            satisfied_customers = sum(1 for f in feedbacks if f.rating >= 4)
            satisfaction_rate = (satisfied_customers / total_feedbacks * 100) if total_feedbacks > 0 else 0
            
            # Get recent feedback (last 5)
            recent_feedbacks = sorted(feedbacks, key=lambda x: x.created_at, reverse=True)[:5]
            recent_feedback_data = []
            
            for feedback in recent_feedbacks:
                recent_feedback_data.append({
                    'id': feedback.id,
                    'title': feedback.title,
                    'content': feedback.content[:100] + '...' if len(feedback.content) > 100 else feedback.content,
                    'rating': feedback.rating,
                    'customer_name': feedback.customer_display_name,
                    'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_ago': feedback.time_ago
                })
            
            return {
                'total_feedbacks': total_feedbacks,
                'average_rating': round(average_rating, 2),
                'rating_distribution': rating_distribution,
                'recent_feedbacks': recent_feedback_data,
                'satisfaction_rate': round(satisfaction_rate, 1)
            }
            
        except Exception as e:
            print(f"Error getting shopkeeper stats: {e}")
            return {
                'total_feedbacks': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                'recent_feedbacks': [],
                'satisfaction_rate': 0
            }
    
    @staticmethod
    def get_shopkeeper_feedback_query(shopkeeper_id):
        """Get query object for shopkeeper's feedback"""
        return Feedback.query.filter_by(shopkeeper_id=shopkeeper_id)
    
    @staticmethod
    def get_feedback_trends(shopkeeper_id, days=30):
        """Get feedback trends over time"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            feedbacks = Feedback.query.filter(
                Feedback.shopkeeper_id == shopkeeper_id,
                Feedback.created_at >= start_date,
                Feedback.created_at <= end_date
            ).all()
            
            # Group by day
            daily_stats = {}
            for feedback in feedbacks:
                day = feedback.created_at.date()
                if day not in daily_stats:
                    daily_stats[day] = {'count': 0, 'total_rating': 0, 'average_rating': 0}
                
                daily_stats[day]['count'] += 1
                daily_stats[day]['total_rating'] += feedback.rating
            
            # Calculate averages
            for day in daily_stats:
                daily_stats[day]['average_rating'] = daily_stats[day]['total_rating'] / daily_stats[day]['count']
            
            return daily_stats
            
        except Exception as e:
            print(f"Error getting feedback trends: {e}")
            return {}
    
    @staticmethod
    def _calculate_response_rate(total_feedback):
        """Calculate response rate"""
        expected_interactions = max(total_feedback * 4, 100)
        
        if expected_interactions > 0:
            rate = round((total_feedback / expected_interactions) * 100)
            return min(rate, 100)
        return 0


class QRCodeService:
    """Service class to handle QR code generation"""
    
    @staticmethod
    def generate_qr_code(data):
        """Generate QR code and return as base64 string"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img_buffer = io.BytesIO()
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None
    
    @staticmethod
    def generate_qr_file(data):
        """Generate QR code and return as file buffer"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img_buffer = io.BytesIO()
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer
            
        except Exception as e:
            print(f"Error generating QR file: {e}")
            return None


class FeedbackService:
    """Service class to handle feedback operations"""
    
    @staticmethod
    def create_feedback(form_data, shopkeeper_id):
        """Create a new feedback entry with proper validation"""
        try:
            # Validate shopkeeper exists and is active
            shopkeeper = Shopkeeper.query.get(shopkeeper_id)
            if not shopkeeper:
                raise ValueError("Shopkeeper not found")
            
            if not shopkeeper.is_active:
                raise ValueError("Shopkeeper account is inactive")
            
            # Create feedback with proper validation
            feedback = Feedback(
                title=form_data.get('title', '').strip(),
                content=form_data.get('content', '').strip(),
                rating=int(form_data.get('rating')),
                customer_name=form_data.get('customer_name', '').strip() if form_data.get('customer_name') else None,
                customer_email=form_data.get('customer_email', '').strip().lower() if form_data.get('customer_email') else None,
                shopkeeper_id=shopkeeper_id
            )
            
            db.session.add(feedback)
            db.session.commit()
            
            return feedback
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating feedback: {e}")
            raise e
    
    @staticmethod
    def broadcast_feedback_update(feedback, stats):
        """Broadcast feedback update via WebSocket"""
        try:
            feedback_data = {
                'id': feedback.id,
                'title': feedback.title,
                'content': feedback.content,
                'rating': feedback.rating,
                'customer_name': feedback.customer_display_name,
                'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': 'Just now',
                'stats': stats
            }
            
            # Only emit if socketio is available and clients are connected
            if socketio:
                socketio.emit('new_feedback', feedback_data, room='dashboard_users')
            
        except Exception as e:
            print(f"Error broadcasting feedback update: {e}")


def get_time_ago(timestamp):
    """Calculate time ago string from timestamp"""
    try:
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except Exception as e:
        print(f"Error calculating time ago: {e}")
        return "Unknown"


def require_shopkeeper(f):
    """Decorator to ensure current user is a shopkeeper"""
    def decorated_function(*args, **kwargs):
        try:
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Check if the current user is actually a shopkeeper
            shopkeeper = Shopkeeper.query.get(current_user.id)
            if not shopkeeper:
                # Check if they're a regular user
                user = User.query.get(current_user.id)
                if user:
                    flash('Access denied. This page is for shopkeepers only.', 'danger')
                    return redirect(url_for('customer.dashboard'))
                else:
                    flash('Account not found. Please contact support.', 'danger')
                    return redirect(url_for('auth.login'))
            
            # Store shopkeeper info in session for later use
            session['shopkeeper_id'] = shopkeeper.id
            session['shopkeeper_username'] = shopkeeper.username
            session['is_shopkeeper'] = True
            
            return f(*args, **kwargs)
            
        except Exception as e:
            print(f"Error in require_shopkeeper decorator: {e}")
            flash('An error occurred while verifying your account.', 'danger')
            return redirect(url_for('auth.login'))
    
    decorated_function.__name__ = f.__name__
    return decorated_function


# ===============================
# MAIN ROUTES
# ===============================

@main.route('/')
def homepage():
    """Homepage route"""
    return render_template('homepage.html')


# routes.py (update customer dashboard route)

@customer.route('/customer/dashboard')
@login_required
def dashboard():
    """Customer dashboard"""
    try:
        # Get recent feedback from this customer using email
        recent_feedbacks = Feedback.query.filter(
            Feedback.customer_email == current_user.email
        ).order_by(Feedback.created_at.desc()).limit(5).all()
        
        # Get feedback count
        feedback_count = Feedback.query.filter(
            Feedback.customer_email == current_user.email
        ).count()
        
        return render_template('customer_dashboard.html', 
                             recent_feedbacks=recent_feedbacks,
                             feedback_count=feedback_count)
    except Exception as e:
        print(f"Error loading customer dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return redirect(url_for('main.homepage'))


@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
@require_shopkeeper
def dashboard():
    try:
        shopkeeper = Shopkeeper.query.get(current_user.id)
        if not shopkeeper:
            flash('Shopkeeper account not found.', 'danger')
            return redirect(url_for('auth.login'))

        # Get recent feedback
        recent_feedback = Feedback.query.filter_by(shopkeeper_id=shopkeeper.id)\
                                        .order_by(Feedback.created_at.desc())\
                                        .limit(10).all()

        # Get stats
        stats = StatisticsService.get_shopkeeper_stats(shopkeeper.id)

        if stats is None:
            flash('Error loading dashboard statistics.', 'warning')
            stats = {
                'total_feedbacks': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                'recent_feedbacks': [],
                'satisfaction_rate': 0
            }

        # NEW: Fetch feedback trend (past 30 days)
        trend_data = Feedback.query \
            .with_entities(func.date(Feedback.created_at).label('date'), func.count().label('count')) \
            .filter_by(shopkeeper_id=shopkeeper.id) \
            .group_by(func.date(Feedback.created_at)) \
            .order_by(func.date(Feedback.created_at)) \
            .all()

        # Format for Chart.js
        feedback_trend = [{'date': str(row.date), 'count': row.count} for row in trend_data]

        return render_template('dashboard.html',
                               all_recent_feedback=recent_feedback,
                               shopkeeper=shopkeeper,
                               total_feedback=stats['total_feedbacks'],
                               average_rating=stats['average_rating'],
                               rating_distribution=stats['rating_distribution'],
                               response_rate=stats['satisfaction_rate'],
                               feedback_trend=feedback_trend  # ✅ Pass to template
                               )
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return render_template('dashboard.html',
                               recent_feedback=[],
                               shopkeeper=None,
                               total_feedbacks=0,
                               average_rating=0,
                               rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                               recent_feedbacks=[],
                               satisfaction_rate=0,
                               feedback_trend=[]
                               )

@main.route('/api/dashboard-stats')
@login_required
@require_shopkeeper
def get_dashboard_stats():
    """API endpoint to get updated dashboard statistics"""
    try:
        # Get shopkeeper ID from session (set by decorator)
        shopkeeper_id = session.get('shopkeeper_id')
        if not shopkeeper_id:
            return jsonify({'error': 'Shopkeeper ID not found in session'}), 400
        
        # Validate shopkeeper still exists
        shopkeeper = Shopkeeper.query.get(shopkeeper_id)
        if not shopkeeper:
            return jsonify({'error': 'Shopkeeper not found'}), 404
        
        stats = StatisticsService.get_shopkeeper_stats(shopkeeper_id)
        if stats is None:
            return jsonify({'error': 'Unable to fetch statistics'}), 500
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main.route('/feedback/<username>', methods=['GET', 'POST'])
def public_feedback(username):
    """Public feedback form accessible without login"""
    try:
        # Get shopkeeper by username with proper validation
        shopkeeper = Shopkeeper.query.filter_by(username=username).first()
        if not shopkeeper:
            flash('Shop not found.', 'danger')
            abort(404)
        
        # Check if shopkeeper is active
        if not shopkeeper.is_active:
            flash('This shop is currently inactive.', 'warning')
            abort(404)
        
        form = PublicFeedbackForm()
        
        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    # Create feedback using the service with proper validation
                    feedback = FeedbackService.create_feedback(
                        form_data={
                            'title': form.title.data,
                            'content': form.content.data,
                            'rating': form.rating.data,
                            'customer_name': form.customer_name.data,
                            'customer_email': form.customer_email.data
                        },
                        shopkeeper_id=shopkeeper.id
                    )
                    
                    # Get updated statistics and broadcast
                    stats = StatisticsService.get_shopkeeper_stats(shopkeeper.id)
                    if stats:
                        FeedbackService.broadcast_feedback_update(feedback, stats)
                    
                    flash('Thank you for your feedback!', 'success')
                    return redirect(url_for('main.feedback_success'))
                    
                except ValueError as ve:
                    flash(f'Validation error: {str(ve)}', 'danger')
                except Exception as e:
                    print(f"Error creating feedback: {e}")
                    flash('Error submitting feedback. Please try again.', 'danger')
            else:
                # Display form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{field}: {error}', 'danger')
        
        return render_template('feedback/public_form.html', 
                             form=form, 
                             shopkeeper=shopkeeper)
                             
    except Exception as e:
        print(f"Error in public_feedback route: {e}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('main.homepage'))
from flask import request, jsonify, render_template

# In routes.py, update the generate_bill route
@main.route('/dashboard/generate-bill', methods=['GET', 'POST'])
@login_required
@require_shopkeeper
def generate_bill():
    items = Item.query.filter_by(shopkeeper_id=current_user.id).all()

    if request.method == 'GET':
        return render_template('generate_bill.html', items=items)

    # POST method - handle bill generation
    selected_items = []
    total_price = 0
    customer_email = request.form.get('customer_email', '').strip().lower()

    for item in items:
        if request.form.get(f'item_{item.id}'):
            try:
                qty = int(request.form.get(f'qty_{item.id}', 1))
                if qty < 1:
                    raise ValueError("Quantity must be at least 1")
            except ValueError:
                qty = 1  # Default to 1 if invalid
            
            
            item_total = qty * item.price
            total_price += item_total
            selected_items.append({
                'item': item,
                'quantity': qty,
                'item_total': item_total
            })

    # Check if any items were selected
    if not selected_items:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return '<div class="alert alert-warning">Please select at least one item to generate a bill.</div>', 400
        else:
            flash('Please select at least one item to generate a bill.', 'warning')
            return redirect(url_for('main.generate_bill'))

    # Check if any items were selected
    if not selected_items:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return '<div class="alert alert-warning">Please select at least one item to generate a bill.</div>', 400
        else:
            flash('Please select at least one item to generate a bill.', 'warning')
            return redirect(url_for('main.generate_bill'))

    from datetime import datetime
    from web.models import Bill, BillItem
    from web.utils import generate_unique_loyalty_code
    from web.models import Bill, BillItem

    # Create the bill
    # Create the bill
    bill = Bill(
        shopkeeper_id=current_user.id,
        total_price=total_price,
        customer_email=customer_email if customer_email else None
    )
    
    # Generate loyalty code if customer email is provided
    if customer_email:
        bill.loyalty_code = generate_unique_loyalty_code()
    
    db.session.add(bill)
    db.session.flush()  # To get the bill ID

    # Create bill items
    for item_data in selected_items:
        bill_item = BillItem(
            bill_id=bill.id,
            item_id=item_data['item'].id,
            quantity=item_data['quantity'],
            price_per_unit=item_data['item'].price
        )
        db.session.add(bill_item)

    db.session.flush()  # To get the bill ID

    # Create bill items
    for item_data in selected_items:
        bill_item = BillItem(
            bill_id=bill.id,
            item_id=item_data['item'].id,
            quantity=item_data['quantity'],
            price_per_unit=item_data['item'].price
        )
        db.session.add(bill_item)

    db.session.commit()

    # AJAX: Return partial template
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'partials/bill_snippet.html',
            selected_items=selected_items,
            total_price=total_price,
            bill=bill,
            bill=bill,
            now=datetime.now
        )

    # Fallback: Redirect to bill page
    return redirect(url_for('main.generate_bill'))


@main.route('/dashboard/item-setup', methods=['GET'])
@login_required
@require_shopkeeper
def item_setup():
    items = Item.query.filter_by(shopkeeper_id=current_user.id).all()
    return render_template('setup.html', items=items)

@main.route('/dashboard/item-setup', methods=['POST'])
@login_required
@require_shopkeeper
def add_item():
    """Add a new item to the shopkeeper's list"""
    try:
        name = request.form.get('name')
        price = float(request.form.get('price'))
        shopkeeper_id = current_user.id

        if not name or price < 0:
            flash("Invalid item data.", "warning")
            return redirect(url_for('main.item_setup'))

        new_item = Item(name=name.strip(), price=price, shopkeeper_id=shopkeeper_id)
        db.session.add(new_item)
        db.session.commit()

        flash("Item added successfully!", "success")
        return redirect(url_for('main.item_setup'))

    except Exception as e:
        db.session.rollback()
        print(f"Error adding item: {e}")
        flash("Failed to add item.", "danger")
        return redirect(url_for('main.item_setup'))

@main.route('/dashboard/delete-item/<int:item_id>', methods=['POST'])
@login_required
@require_shopkeeper
def delete_item(item_id):
    """Delete an item from the shopkeeper's list"""
    try:
        item = Item.query.get(item_id)
        if item and item.shopkeeper_id == current_user.id:
            db.session.delete(item)
            db.session.commit()
            flash("Item deleted successfully!", "success")
        else:
            flash("Item not found or unauthorized.", "danger")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting item: {e}")
        flash("Failed to delete item.", "danger")
    return redirect(url_for('main.item_setup'))
    
@main.route('/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    rating = int(request.form.get('rating'))
    feedback_text = request.form.get('feedback_text')
    bill_id = request.form.get('bill_id')  # This must be sent with form
    customer_id = current_user.id

    bill = Bill.query.get_or_404(bill_id)
    shopkeeper = Shopkeeper.query.get_or_404(bill.shopkeeper_id)

    # Save feedback
    feedback = Feedback(
        rating=rating,
        text=feedback_text,
        customer_email=current_user.email,
        customer_id=customer_id,
        bill_id=bill.id
    )
    db.session.add(feedback)

    # Loyalty logic
    if (
        bill.total_amount >= shopkeeper.minimum_spend_threshold and
        rating >= 4 and
        len(feedback_text.strip().split()) > 20
    ):
        if bill.loyalty_code is None:
            from web.utils import generate_unique_loyalty_code
            bill.loyalty_code = generate_unique_loyalty_code()

    db.session.commit()
    return redirect(url_for('main.feedback_success'))

@main.route('/feedback/success')
def feedback_success():
    """Feedback submission success page"""
    return render_template('feedback/success.html')

# 1. Fix the create_feedback route for logged-in users
@main.route('/my-feedback', methods=['GET', 'POST'])
@login_required
def create_feedback():
    """Private feedback form for logged-in users"""
    try:
        form = FeedbackForm()
        
        # Get available shopkeepers for selection
        shopkeepers = Shopkeeper.query.filter_by(is_active=True).all()
        
        if form.validate_on_submit():
            try:
                # Get shopkeeper_id from form data
                shopkeeper_id = request.form.get('shopkeeper_id')
                
                if not shopkeeper_id:
                    flash('Please select a shopkeeper.', 'danger')
                    return render_template('feedback/create.html', form=form, shopkeepers=shopkeepers)
                
                # Validate shopkeeper exists
                shopkeeper = Shopkeeper.query.get(int(shopkeeper_id))
                if not shopkeeper:
                    flash('Selected shopkeeper not found.', 'danger')
                    return render_template('feedback/create.html', form=form, shopkeepers=shopkeepers)
                
                # Create feedback using the service
                feedback = FeedbackService.create_feedback(
                    form_data={
                        'title': form.title.data,
                        'content': form.content.data,
                        'rating': form.rating.data,
                        'customer_name': current_user.full_name,
                        'customer_email': current_user.email
                    },
                    shopkeeper_id=int(shopkeeper_id),
                )
                
                # Get updated statistics and broadcast
                stats = StatisticsService.get_shopkeeper_stats(int(shopkeeper_id))
                if stats:
                    FeedbackService.broadcast_feedback_update(feedback, stats)
                
                flash('Feedback submitted successfully!', 'success')
                return redirect(url_for('customer.dashboard'))
                
            except ValueError as ve:
                flash(f'Validation error: {str(ve)}', 'danger')
            except Exception as e:
                print(f"Error creating feedback: {e}")
                flash('Error submitting feedback. Please try again.', 'danger')
        
        return render_template('feedback/create.html', form=form, shopkeepers=shopkeepers)
        
    except Exception as e:
        print(f"Error in create_feedback route: {e}")
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('customer.dashboard'))

@main.route('/generate-qr')
@login_required
@require_shopkeeper
def generate_qr():
    """Generate QR code for shopkeeper's feedback form"""
    try:
        shopkeeper = Shopkeeper.query.filter_by(id=current_user.id).first()
        if not shopkeeper or not shopkeeper.username:
            flash('Username not found. Please contact support.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        feedback_url = url_for('main.public_feedback', 
                              username=shopkeeper.username, 
                              _external=True)
        
        qr_image = QRCodeService.generate_qr_code(feedback_url)
        
        if qr_image is None:
            flash('Error generating QR code. Please try again.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return render_template('qr_code.html', 
                             qr_image=qr_image, 
                             feedback_url=feedback_url)
                             
    except Exception as e:
        print(f"Error generating QR code: {e}")
        flash('Error generating QR code. Please try again.', 'danger')
        return redirect(url_for('main.dashboard'))


@main.route('/download-qr')
@login_required
@require_shopkeeper
def download_qr():
    """Download QR code as PNG file"""
    try:
        shopkeeper = Shopkeeper.query.filter_by(id=current_user.id).first()
        if not shopkeeper or not shopkeeper.username:
            flash('Username not found. Please contact support.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        feedback_url = url_for('main.public_feedback', 
                              username=shopkeeper.username, 
                              _external=True)
        
        img_buffer = QRCodeService.generate_qr_file(feedback_url)
        
        if img_buffer is None:
            flash('Error generating QR code file. Please try again.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        response = make_response(img_buffer.getvalue())
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = 'attachment; filename=feedback_qr_code.png'
        
        return response
        
    except Exception as e:
        print(f"Error downloading QR code: {e}")
        flash('Error downloading QR code. Please try again.', 'danger')
        return redirect(url_for('main.dashboard'))


@main.route('/dashboard/my-feedback')
@login_required
@require_shopkeeper
def my_feedback_dashboard():
    """Dashboard for shopkeeper to view their feedback"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Get feedback with pagination
        feedbacks = Feedback.query.filter_by(shopkeeper_id=current_user.id)\
                                 .order_by(Feedback.created_at.desc())\
                                 .paginate(page=page, per_page=per_page, error_out=False)
        
        # Get statistics
        stats = StatisticsService.get_shopkeeper_stats(current_user.id)
        if stats is None:
            stats = {
                'total_feedbacks': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        return render_template('feedback/all_feedback.html', 
                       feedback_list=feedbacks.items,
                       stats=stats)
                             
    except Exception as e:
        print(f"Error loading feedback dashboard: {e}")
        flash('Error loading feedback dashboard. Please try again.', 'danger')
        return redirect(url_for('main.dashboard'))
    

from datetime import datetime, timedelta
import calendar

# Add to routes.py
@main.route('/analytics')
@login_required
@require_shopkeeper
def analytics():
    # Add this at the start of your route to verify DB connection
    try:
        test_query = Shopkeeper.query.limit(1).all()
        print(f"DEBUG: DB test query: {test_query}")
    except Exception as db_error:
        print(f"DEBUG: DB error: {str(db_error)}")
    try:
        print("DEBUG: Entered analytics route")  # Debug log
        shopkeeper = Shopkeeper.query.get(current_user.id)
        print(f"DEBUG: Shopkeeper: {shopkeeper}")  # Debug log
        
        if not shopkeeper:
            flash('Shopkeeper account not found.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Get stats
        stats = StatisticsService.get_shopkeeper_stats(shopkeeper.id)
        print(f"DEBUG: Stats: {stats}")  # Debug log
        
        if stats is None:
            stats = {
                'total_feedbacks': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                'satisfaction_rate': 0
            }
        
        # Get feedback trend for the last 6 months
        monthly_trend = []
        current_date = datetime.utcnow()
        print(f"DEBUG: Current date: {current_date}")  # Debug log
        
        for i in range(5, -1, -1):
            month_date = current_date - timedelta(days=30*i)
            print(f"DEBUG: Processing month {i}: {month_date}")  # Debug log
            
            try:
                month_name = calendar.month_abbr[month_date.month]
                year = month_date.year
                
                # Get feedback count for the month
                start_date = month_date.replace(day=1, hour=0, minute=0, second=0)
                end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
                
                print(f"DEBUG: Querying between {start_date} and {end_date}")  # Debug log
                
                count = Feedback.query.filter(
                    Feedback.shopkeeper_id == shopkeeper.id,
                    Feedback.created_at >= start_date,
                    Feedback.created_at < end_date
                ).count()
                
                monthly_trend.append({
                    'month': f"{month_name} {year}",
                    'count': count
                })
                
            except Exception as month_error:
                print(f"ERROR processing month {i}: {str(month_error)}")
                monthly_trend.append({
                    'month': f"Month {i}",
                    'count': 0
                })
        
        # Get feedback by day of week
        day_counts = [0] * 7  # Sunday to Saturday
        feedbacks = Feedback.query.filter_by(shopkeeper_id=shopkeeper.id).all()
        
        for feedback in feedbacks:
            if feedback.created_at:
                try:
                    day_counts[feedback.created_at.weekday()] += 1
                except Exception as day_error:
                    print(f"ERROR processing day count: {str(day_error)}")
        
        print("DEBUG: Successfully processed all data")  # Debug log
        return render_template('analytics.html',
                            total_feedback=stats['total_feedbacks'],
                            average_rating=stats['average_rating'],
                            rating_distribution=stats['rating_distribution'],
                            monthly_trend=monthly_trend,
                            day_counts=day_counts,
                            shopkeeper=shopkeeper)
        
    except Exception as e:
        print(f"ERROR in analytics route: {str(e)}")  # More detailed error
        print(f"ERROR Type: {type(e)}")  # Error type
        import traceback
        traceback.print_exc()  # Full traceback
        flash('Error loading analytics. Please try again.', 'danger')
        return redirect(url_for('main.dashboard'))


# ===============================
# WEBSOCKET EVENT HANDLERS
# ===============================

def register_socketio_events(socketio):
    """Register WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        try:
            print(f'Client connected: {request.sid}')
        except Exception as e:
            print(f'Error handling connect: {e}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            print(f'Client disconnected: {request.sid}')
        except Exception as e:
            print(f'Error handling disconnect: {e}')
    
    @socketio.on('join_dashboard')
    def handle_join_dashboard():
        try:
            join_room('dashboard_users')
            emit('status', {'msg': 'Connected to dashboard updates'})
            print(f'Client {request.sid} joined dashboard room')
        except Exception as e:
            print(f'Error joining dashboard room: {e}')
            emit('error', {'msg': 'Failed to join dashboard updates'})
    
    @socketio.on('leave_dashboard')
    def handle_leave_dashboard():
        try:
            leave_room('dashboard_users')
            emit('status', {'msg': 'Disconnected from dashboard updates'})
            print(f'Client {request.sid} left dashboard room')
        except Exception as e:
            print(f'Error leaving dashboard room: {e}')
    
    @socketio.on('request_feedback_update')
    def handle_feedback_update_request():
        """Send latest feedback to requesting client"""
        try:
            # Get shopkeeper ID from session or request
            shopkeeper_id = session.get('shopkeeper_id')
            if not shopkeeper_id:
                emit('error', {'msg': 'No shopkeeper ID found'})
                return
            
            latest_feedback = Feedback.query.filter_by(shopkeeper_id=shopkeeper_id)\
                                          .order_by(Feedback.created_at.desc())\
                                          .limit(10).all()
            
            feedback_list = []
            for feedback in latest_feedback:
                feedback_data = {
                    'id': feedback.id,
                    'title': feedback.title,
                    'content': feedback.content,
                    'rating': feedback.rating,
                    'customer_name': feedback.customer_display_name,
                    'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_ago': feedback.time_ago
                }
                feedback_list.append(feedback_data)
            
            emit('feedback_update', {'feedback_list': feedback_list})
            
        except Exception as e:
            print(f"Error in feedback update request: {e}")
            emit('error', {'msg': 'Failed to fetch feedback updates'})