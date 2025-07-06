from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from web import db
from web.models import User, Feedback ,Shopkeeper , ItemFeedback , Item
from web.forms import FeedbackForm, PublicFeedbackForm
import qrcode
import io
import base64
from datetime import datetime, timedelta
import json
from sqlalchemy import func
from web import socketio
import qrcode
import io
import base64
from flask import abort
from flask import render_template, url_for
from flask_login import login_required, current_user
from flask import session


#customer routes

customer = Blueprint('customer', __name__)
@customer.route('/customer/dashboard')
@login_required
def dashboard():
    return render_template('customer_dashboard.html')


#main routes
main = Blueprint('main', __name__)
@main.route('/')
def homepage():
    return render_template('homepage.html')

from web.models import Item
@main.route('/dashboard',methods=['GET', 'POST']) #added on 29
@login_required
def dashboard():
    #
    shopkeeper_id = session.get('shopkeeper_id')  # Or however you track login
    all_recent_feedback = Feedback.query.join(Feedback.item).filter(
        Item.shopkeeper_id == shopkeeper_id
    ).order_by(Feedback.created_at.desc()).limit(10).all()

    # Load item feedbacks for each feedback
    feedback_with_items = []
    for feedback in all_recent_feedback:
        item_feedbacks = ItemFeedback.query.filter_by(feedback_id=feedback.id).join(Item).all()
        feedback_with_items.append({
            'feedback': feedback,
            'item_feedbacks': item_feedbacks
        })
    
    
    
    
    
    
    
    ##
    if not isinstance (current_user, Shopkeeper):
        abort(403) 
        # Add item logic
    if request.method == 'POST':
        item_name = request.form.get('item_name')
        if item_name:
            new_item = Item(name=item_name, shopkeeper_id=current_user.id)
            db.session.add(new_item)
            db.session.commit()
            flash(f'Item "{item_name}" added successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    
    items = Item.query.filter_by(shopkeeper_id=current_user.id).all()

    feedback_query = Feedback.query.join(Feedback.item).filter(Item.shopkeeper_id == current_user.id)

    recent_feedback = Feedback.query.filter_by(user_id=current_user.id)\
                                  .order_by(Feedback.created_at.desc())\
                                  .limit(5).all()
    all_recent_feedback = feedback_query.order_by(Feedback.created_at.desc()).limit(10).all()
    
    total_feedback = Feedback.query.count()
    
    
    avg_rating_result = db.session.query(func.avg(Feedback.rating)).scalar()
    average_rating = round(avg_rating_result, 1) if avg_rating_result else 0.0
    
    # Get rating distribution
    rating_distribution = get_rating_distribution()    
    # Calculate some mock metrics for now (you can replace with real calculations)
    active_customers = get_active_customers_count()
    response_rate = calculate_response_rate()
    
    return render_template('dashboard.html', 
                         recent_feedback=recent_feedback,
                         total_feedback=total_feedback,
                         average_rating=average_rating,
                         rating_distribution=rating_distribution,
                         active_customers=active_customers,
                         response_rate=response_rate,
                         all_recent_feedback=all_recent_feedback
                         , items=items)#added on 29

def get_rating_distribution():
    """Get the distribution of ratings (1-5 stars)"""
    total_feedback = Feedback.query.count()
    if total_feedback == 0:
        return {i: 0 for i in range(1, 6)}
    
    distribution = {}
    for rating in range(1, 6):
        count = Feedback.query.filter_by(rating=rating).count()
        percentage = round((count / total_feedback) * 100) if total_feedback > 0 else 0
        distribution[rating] = percentage
    
    return distribution

def get_active_customers_count():
    """Calculate active customers (unique feedback providers in last 30 days)"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Count unique customer names and emails from recent feedback
    recent_feedback = Feedback.query.filter(Feedback.created_at >= thirty_days_ago).all()
    unique_customers = set()
    
    for feedback in recent_feedback:
        if feedback.customer_name:
            unique_customers.add(feedback.customer_name.lower())
        elif feedback.customer_email:
            unique_customers.add(feedback.customer_email.lower())
        elif feedback.user_id:
            unique_customers.add(f"user_{feedback.user_id}")
        else:
            unique_customers.add("anonymous")
    
    return len(unique_customers)

def calculate_response_rate():
    """Calculate response rate (feedback received vs expected interactions)"""
    #This is a simplified calculation - you might want to implement based on your business logic
    total_feedback = Feedback.query.count()
    # Assuming some base number of interactions (you can modify this logic)
    expected_interactions = max(total_feedback * 4, 100)  # Simple assumption
    
    if expected_interactions > 0:
        rate = round((total_feedback / expected_interactions) * 100)
        return min(rate, 100)  # Cap at 100%
    return 0

@main.route('/api/dashboard-stats')
@login_required
def get_dashboard_stats():
    """API endpoint to get updated dashboard statistics"""
    total_feedback = Feedback.query.count()
    
    # Calculate average rating
    avg_rating_result = db.session.query(func.avg(Feedback.rating)).scalar()
    average_rating = round(avg_rating_result, 1) if avg_rating_result else 0.0
    
    # Get rating distribution
    rating_distribution = get_rating_distribution()
    
    # Get other metrics
    active_customers = get_active_customers_count()
    response_rate = calculate_response_rate()
    
    return jsonify({
        'total_feedback': total_feedback,
        'average_rating': average_rating,
        'rating_distribution': rating_distribution,
        'active_customers': active_customers,
        'response_rate': response_rate
    })

# Public feedback form (accessible without login)
@main.route('/feedback/<username>', methods=['GET', 'POST'])
def public_feedback(username):
    form = PublicFeedbackForm()

    # Get shopkeeper by username
    shopkeeper = Shopkeeper.query.filter_by(username=username).first_or_404()
    shopkeeper_id = shopkeeper.id

    # Fetch items belonging to the shopkeeper
    from web.models import Item
    items = Item.query.filter_by(shopkeeper_id=shopkeeper_id).all()

    # Assign items to form dropdown
    form.items = items
    form.item_id.choices = [(item.id, item.name) for item in items]

    

    is_valid=form.validate_on_submit()
    print("Form submitted:", form.validate_on_submit())
    print("Form errors:", form.errors)
    if is_valid:
        feedback = Feedback(
            title=form.title.data,
            content=form.content.data,
            rating=int(form.rating.data),
            customer_name=form.customer_name.data,
            customer_email=form.customer_email.data,
            user_id=None,
            item_id=form.item_id.data,
            #shopkeeper_id=shopkeeper_id
        )

        db.session.add(feedback)

        #Save individual item ratings (if any)
        for item in items:
            rating_key = f'item_rating_{item.id}'
            rating_value = request.form.get(rating_key)
            if rating_value:
                item_feedback = Feedback(
                    title=form.title.data,
                    content=form.content.data,
                    rating=int(rating_value),
                    customer_name=form.customer_name.data,
                    customer_email=form.customer_email.data,
                    item_id=item.id,
                    user_id=None,
                    #shopkeeper_id=shopkeeper_id
                )
                db.session.add(item_feedback)
        # Commit all feedback to the database   
        db.session.commit()

        #Flash + socket + stats
        

    
        
        total_feedback = Feedback.query.count()
        avg_rating_result = db.session.query(func.avg(Feedback.rating)).scalar()
        average_rating = round(avg_rating_result, 1) if avg_rating_result else 0.0
        rating_distribution = get_rating_distribution()
        active_customers = get_active_customers_count()
        response_rate = calculate_response_rate()

        feedback_data = {
            'id': feedback.id,
            'title': feedback.title,
            'content': feedback.content,
            'rating': feedback.rating,
            'customer_name': feedback.customer_name or 'Anonymous',
            'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': 'Just now',
            'stats': {
                'total_feedback': total_feedback,
                'average_rating': average_rating,
                'rating_distribution': rating_distribution,
                'active_customers': active_customers,
                'response_rate': response_rate
            }
        }

        socketio.emit('new_feedback', feedback_data, room='dashboard_users')
        
        return redirect(url_for('main.feedback_success'))

    return render_template('feedback/public_form.html', form=form, items=items, shopkeeper=shopkeeper)


@main.route('/feedback/success')
def feedback_success():
    return render_template('feedback/success.html')

# Private feedback form for logged-in users
@main.route('/my-feedback', methods=['GET', 'POST'])
@login_required
def create_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            title=form.title.data,
            content=form.content.data,
            rating=int(form.rating.data),
            user_id=current_user.id
        )
        db.session.add(feedback)
        db.session.commit()
        
        # Get updated statistics after adding new feedback
        total_feedback = Feedback.query.count()
        avg_rating_result = db.session.query(func.avg(Feedback.rating)).scalar()
        average_rating = round(avg_rating_result, 1) if avg_rating_result else 0.0
        rating_distribution = get_rating_distribution()
        active_customers = get_active_customers_count()
        response_rate = calculate_response_rate()
        
        # Emit real-time update to all connected dashboard users
        from web import socketio
        feedback_data = {
            'id': feedback.id,
            'title': feedback.title,
            'content': feedback.content,
            'rating': feedback.rating,
            'customer_name': current_user.full_name,
            'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': 'Just now',
            # Include updated statistics
            'stats': {
                'total_feedback': total_feedback,
                'average_rating': average_rating,
                'rating_distribution': rating_distribution,
                'active_customers': active_customers,
                'response_rate': response_rate
            }
        }
        socketio.emit('new_feedback', feedback_data, room='dashboard_users')
        
        flash('Feedback submitted successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('feedback/create.html', form=form)

# QR Code generation route
@main.route('/generate-qr')
@login_required
def generate_qr():
    # Get current user's username (e.g., a shopkeeper)
    username = current_user.username
    
    # Generate full URL to public feedback page for that user
    feedback_url = url_for('main.public_feedback', username=username, _external=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(feedback_url)
    qr.make(fit=True)

    # Convert to base64 for HTML display
    img_buffer = io.BytesIO()
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    return render_template('qr_code.html', qr_image=img_base64, feedback_url=feedback_url)

# Route to download QR code as PNG
@main.route('/download-qr')
@login_required
def download_qr():
    from flask import make_response  # Ensure this import exists
    import qrcode, io
    from flask_login import current_user

    # Use the logged-in user's username
    username = current_user.username

    # Full URL to the public feedback form for that shopkeeper
    feedback_url = url_for('main.public_feedback', username=username, _external=True)

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(feedback_url)
    qr.make(fit=True)

    # Save to BytesIO
    img_buffer = io.BytesIO()
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    # Return image as file download
    response = make_response(img_buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Content-Disposition'] = 'attachment; filename=feedback_qr_code.png'

    return response


# Route to view all feedback (for admin/business owner)
@main.route('/all-feedback')
@login_required
def view_all_feedback():
    # Get all feedback (both from logged-in users and anonymous)
    all_feedback = Feedback.query.order_by(Feedback.created_at.desc()).all()
    
    return render_template('feedback/all_feedback.html', feedback_list=all_feedback)

# WebSocket event handlers
def register_socketio_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        print(f'Client connected: {request.sid}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f'Client disconnected: {request.sid}')
    
    @socketio.on('join_dashboard')
    def handle_join_dashboard():
        join_room('dashboard_users')
        emit('status', {'msg': 'Connected to dashboard updates'})
        print(f'Client {request.sid} joined dashboard room')
    
    @socketio.on('leave_dashboard')
    def handle_leave_dashboard():
        leave_room('dashboard_users')
        emit('status', {'msg': 'Disconnected from dashboard updates'})
        print(f'Client {request.sid} left dashboard room')
    
    @socketio.on('request_feedback_update')
    def handle_feedback_update_request():
        # Send latest feedback to the requesting client
        latest_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(10).all()
        feedback_list = []
        for feedback in latest_feedback:
            feedback_data = {
                'id': feedback.id,
                'title': feedback.title,
                'content': feedback.content,
                'rating': feedback.rating,
                'customer_name': feedback.customer_name or 'Anonymous',
                'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': get_time_ago(feedback.created_at)
            }
            feedback_list.append(feedback_data)
        
        emit('feedback_update', {'feedback_list': feedback_list})

def get_time_ago(timestamp):
    """Calculate time ago string from timestamp"""
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