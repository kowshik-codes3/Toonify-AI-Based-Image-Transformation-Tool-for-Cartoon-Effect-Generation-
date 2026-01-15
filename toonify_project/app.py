from flask import Flask, request, render_template, session, redirect, url_for, flash, send_file
from flask_cors import CORS
from auth import login_user, signup_user
from database import (create_connection, create_users_table, get_user_profile, 
                     update_user_profile, add_cartoonized_image, get_user_cartoonized_images,
                     get_cartoonized_image_by_id, delete_cartoonized_image, get_user_paid_cartoonized_images,
                     create_feedback_table, add_user_feedback, get_user_feedback, has_user_given_feedback,
                     get_gallery_analytics)
import database
from PIL import Image
import io
import base64
import os

from cartoonization import get_cartoonization_styles, apply_cartoonization
from dynamic_pricing import get_price_for_style, get_style_display_info

def get_available_styles():
    return get_cartoonization_styles()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-in-production'  
CORS(app) 

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

conn = create_connection()
if conn:
    create_users_table(conn)
    create_feedback_table(conn)
else:
    print("Error: Could not connect to the database.")

# Register payments blueprint (Razorpay)
try:
    from payments import payments_bp
    app.register_blueprint(payments_bp)
except Exception as e:
    # Blueprint registration failure should not crash the app at import time
    print('Warning: Could not register payments blueprint:', e)


@app.route('/')
def home():
    
    return render_template('home.html')

@app.route('/pricing')
def pricing():
    # Show pricing page
    return render_template('pricing.html')

@app.route('/gallery')
def gallery():
    # Get analytics data for the gallery page
    conn = database.create_connection()
    analytics_data = {}
    
    if conn:
        try:
            analytics_data = database.get_gallery_analytics(conn)
        except Exception as e:
            print(f"Error fetching gallery analytics: {e}")
            analytics_data = {
                'total_transformations': 0,
                'total_users': 0,
                'total_feedback': 0,
                'average_rating': 0,
                'satisfaction_rate': 0,
                'recent_feedback': 0,
                'five_star': 0,
                'four_star': 0,
                'three_star': 0,
                'two_star': 0,
                'one_star': 0
            }
        finally:
            conn.close()
    
    # Show gallery page with analytics data
    return render_template('gallery.html', analytics=analytics_data)

@app.route('/app')
def index():
    if 'user_email' in session:
        return render_template('dashboard.html', user_email=session['user_email'])
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    # Check if we need to show feedback overlay
    feedback_image_id = session.pop('show_feedback_for_image', None)
    if feedback_image_id and not has_user_given_feedback(conn, user_profile['id'], feedback_image_id):
        return redirect(url_for('feedback_page', image_id=feedback_image_id))
    
    # Just get basic stats, no image loading for dashboard
    from database import get_user_stats
    try:
        stats = get_user_stats(conn, user_profile['id'])
    except:
        stats = {'total_images': 0, 'total_styles': 0}
    
    return render_template('dashboard.html', 
                         user_email=session['user_email'], 
                         user_profile=user_profile,
                         stats=stats, 
                         session=session)

@app.route('/download_image/<int:image_id>')
def download_image(image_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    # Check if image is paid for before allowing download
    from database import is_image_paid
    if not is_image_paid(conn, image_id, user_profile['id']):
        flash('Payment required. Please complete payment to download this image.', 'error')
        return redirect(url_for('history'))
    
    image_record = get_cartoonized_image_by_id(conn, image_id, user_profile['id'])
    if not image_record:
        flash('Image not found or access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Ensure file path is absolute and exists
    file_path = os.path.abspath(image_record['cartoon_file_path'])
    if not os.path.exists(file_path):
        flash('Image file not found on server. Please regenerate the image.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Set session flag to show feedback overlay after download
        session['show_feedback_for_image'] = image_id
        
        # Create safe filename for download
        safe_filename = f"{image_record['style_name']}_{image_record['original_filename']}"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
        
        print(f"DEBUG: Downloading file {file_path} as {safe_filename}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='image/jpeg'
        )
    except Exception as e:
        print(f"ERROR: Download failed: {str(e)}")
        flash(f'Error downloading image: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/feedback_page/<int:image_id>')
def feedback_page(image_id):
    """Show feedback page after successful download."""
    print(f"DEBUG: Feedback page requested for image {image_id}")
    
    if 'user_email' not in session:
        print("DEBUG: No user in session, redirecting to login")
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        print("DEBUG: No user profile found, redirecting to logout")
        return redirect(url_for('logout'))
    
    # Check if user has already given feedback for this image
    if has_user_given_feedback(conn, user_profile['id'], image_id):
        flash('You have already provided feedback for this image.', 'info')
        return redirect(url_for('dashboard'))
    
    image_record = get_cartoonized_image_by_id(conn, image_id, user_profile['id'])
    if not image_record:
        print(f"DEBUG: No image record found for image {image_id} and user {user_profile['id']}")
        flash('Image not found or access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    print(f"DEBUG: Showing feedback page for image {image_id}")
    return render_template('feedback.html', image=image_record, user_profile=user_profile, session=session)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """Handle feedback submission."""
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    try:
        image_id = int(request.form.get('image_id'))
        rating = int(request.form.get('rating'))
        feedback_text = request.form.get('feedback_text', '').strip()
        
        # Validate rating
        if rating < 1 or rating > 5:
            flash('Invalid rating. Please select a rating between 1 and 5.', 'error')
            return redirect(url_for('feedback_page', image_id=image_id))
        
        # Add feedback to database
        feedback_id = add_user_feedback(conn, user_profile['id'], image_id, rating, feedback_text)
        
        if feedback_id:
            flash('Thank you for your feedback! Your rating helps us improve our service.', 'success')
            # Clear the session flag
            session.pop('show_feedback_for_image', None)
            print(f"DEBUG: Feedback submitted successfully for image {image_id} by user {user_profile['id']}")
        else:
            flash('Error submitting feedback. Please try again.', 'error')
            return redirect(url_for('feedback_page', image_id=image_id))
        
        return redirect(url_for('dashboard'))
        
    except (ValueError, TypeError) as e:
        flash('Invalid form data. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error submitting feedback: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_image/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    deleted_paths = delete_cartoonized_image(conn, image_id, user_profile['id'])
    
    if deleted_paths:
        cartoon_path, original_path = deleted_paths
        try:
            if os.path.exists(cartoon_path):
                os.remove(cartoon_path)
                print(f"SUCCESS: Deleted cartoon file: {cartoon_path}")
        except Exception as e:
            print(f"WARNING: Error deleting cartoon file: {e}")
        flash('Image deleted successfully.', 'success')
    else:
        flash('Image not found or already deleted.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/profile')
def profile():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    from database import get_user_profile
    user_profile = get_user_profile(conn, session['user_email'])
    
    if not user_profile:
        return redirect(url_for('logout'))
    
    return render_template('profile.html', user=user_profile, user_profile=user_profile, session=session)

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    from database import get_user_profile, update_user_profile, check_user_exists_exclude_current
    from auth import hash_security_answer
    
    user_profile = get_user_profile(conn, session['user_email'])
    
    if not user_profile:
        return redirect(url_for('logout'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        date_of_birth = request.form.get('dob')
        age = request.form.get('age')
        gender = request.form.get('gender')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')
        
        # Validation
        if not all([username, email, date_of_birth, age, gender, security_question]):
            return render_template('edit_profile.html', user=user_profile, 
                                 message='All fields except security answer are required', 
                                 message_type='error', session=session)
        
        try:
            age = int(age)
            if age < 13 or age > 120:
                return render_template('edit_profile.html', user=user_profile, 
                                     message='Age must be between 13 and 120', 
                                     message_type='error', session=session)
        except ValueError:
            return render_template('edit_profile.html', user=user_profile, 
                                 message='Invalid age format', 
                                 message_type='error', session=session)
        
        if check_user_exists_exclude_current(conn, username, email, user_profile['id']):
            return render_template('edit_profile.html', user=user_profile, 
                                 message='Username or email already exists', 
                                 message_type='error', session=session)
        
        # Hash security answer if provided
        security_answer_hash = None
        if security_answer and security_answer.strip():
            security_answer_hash = hash_security_answer(security_answer)
        
        # Update user profile
        if update_user_profile(conn, user_profile['id'], username, email, date_of_birth, 
                             age, gender, security_question, security_answer_hash):
            
            if email != session['user_email']:
                session['user_email'] = email
            
            return render_template('profile.html', 
                                 user=get_user_profile(conn, email), 
                                 message='Profile updated successfully!', 
                                 message_type='success', session=session)
        else:
            return render_template('edit_profile.html', user=user_profile, 
                                 message='Error updating profile. Please try again.', 
                                 message_type='error', session=session)
    
    return render_template('edit_profile.html', user=user_profile, session=session)

@app.route('/history')
def history():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    # Only show PAID images in the history page
    user_images = get_user_paid_cartoonized_images(conn, user_profile['id'], limit=50)
    image_gallery = []
    unique_styles = set()
    total_size_mb = 0
    
    for img in user_images:
        try:
            # Read the cartoon image file and encode to base64
            if os.path.exists(img['cartoon_file_path']):
                with open(img['cartoon_file_path'], 'rb') as file:
                    image_data = base64.b64encode(file.read()).decode('utf-8')
                    
                image_gallery.append({
                    'id': img['id'],
                    'original_filename': img['original_filename'],
                    'cartoon_filename': img['cartoon_filename'],
                    'style_name': img['style_name'],
                    'image_width': img['image_width'],
                    'image_height': img['image_height'],
                    'file_size_mb': img['file_size_mb'],
                    'created_at': img['created_at'],
                    'cartoon_base64': image_data,
                    'is_paid': True  # All images here are paid
                })
                
                unique_styles.add(img['style_name'])
                total_size_mb += float(img['file_size_mb'] or 0)
                
        except Exception as e:
            print(f"Error processing image {img.get('id', 'unknown')}: {e}")
    
    return render_template('history.html', 
                         user_email=session['user_email'], 
                         user_profile=user_profile,
                         image_gallery=image_gallery,
                         unique_styles=unique_styles,
                         total_size_mb=round(total_size_mb, 2),
                         session=session)

@app.route('/settings')
def settings():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    return render_template('edit_profile.html', 
                         user=user_profile, 
                         user_profile=user_profile,
                         session=session,
                         page_title="Settings - Manage Your Account")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template('login.html', message='Email and password are required', message_type='error')
        
        if login_user(conn, email, password):
            session['user_email'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', message='Invalid email or password', message_type='error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        date_of_birth = request.form.get('dob')
        age = request.form.get('age')
        gender = request.form.get('gender')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')
        
        if not all([username, email, password, date_of_birth, age, gender, security_question, security_answer]):
            return render_template('signup.html', message='All fields are required', message_type='error')
        try:
            age = int(age)
            if age < 13 or age > 120:
                return render_template('signup.html', message='Age must be between 13 and 120', message_type='error')
        except ValueError:
            return render_template('signup.html', message='Invalid age format', message_type='error')
        
        if len(password) < 8:
            return render_template('signup.html', message='Password must be at least 8 characters long', message_type='error')
        
        if len(security_answer.strip()) < 2:
            return render_template('signup.html', message='Security answer must be at least 2 characters long', message_type='error')
        
        if signup_user(conn, username, email, password, date_of_birth, age, gender, security_question, security_answer):
            return render_template('login.html', message='Account created successfully! Please log in.', message_type='success')
        else:
            return render_template('signup.html', message='Username or email already exists', message_type='error')
    
    return render_template('signup.html')

@app.route('/toonify', methods=['GET', 'POST'])
def toonify():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_profile = get_user_profile(conn, session['user_email'])
    if not user_profile:
        return redirect(url_for('logout'))
    
    if request.method == 'GET':
        styles = get_available_styles()
        # Import pricing functions
        from dynamic_pricing import get_all_styles_with_pricing
        styles_with_pricing = get_all_styles_with_pricing()
        return render_template('toonify.html', user_email=session['user_email'], user_profile=user_profile, 
                             session=session, available_styles=styles, styles_with_pricing=styles_with_pricing)
    
    # Debug: Log POST request details
    print(f"POST request received:")
    print(f"  Form data: {dict(request.form)}")
    print(f"  Files: {list(request.files.keys())}")
    print(f"  Content type: {request.content_type}")
    
    reprocess_existing = request.form.get('reprocess_existing')
    
    if reprocess_existing:
        return handle_reprocess_image()
    if 'image' not in request.files:
        styles = get_available_styles()
        from dynamic_pricing import get_all_styles_with_pricing
        styles_with_pricing = get_all_styles_with_pricing()
        return render_template('toonify.html', user_email=session['user_email'], user_profile=user_profile,
                             message='No image uploaded', message_type='error', session=session, 
                             available_styles=styles, styles_with_pricing=styles_with_pricing)
    
    file = request.files['image']
    if file.filename == '':
        styles = get_available_styles()
        from dynamic_pricing import get_all_styles_with_pricing
        styles_with_pricing = get_all_styles_with_pricing()
        return render_template('toonify.html', user_email=session['user_email'], user_profile=user_profile, 
                             message='No image selected', message_type='error', session=session, 
                             available_styles=styles, styles_with_pricing=styles_with_pricing)
    
    if file and allowed_file(file.filename):
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb > 5:
                return render_template('toonify.html', user_email=session['user_email'], user_profile=user_profile,
                                     message=f'File size ({file_size_mb:.1f} MB) exceeds 5 MB limit. Please upload a smaller image.', 
                                     message_type='error', session=session)
            
            image = Image.open(file.stream)
            
            width, height = image.size
            format_type = image.format
            # Convert to highest quality format for frontend display
            img_buffer = io.BytesIO()
            # Use JPEG with maximum quality for better web display
            if image.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB for JPEG compatibility
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                rgb_image.save(img_buffer, format='JPEG', quality=100, optimize=False)
            else:
                image.save(img_buffer, format='JPEG', quality=100, optimize=False)
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode()
            
            filename = f"uploaded_{session['user_email'].replace('@', '_').replace('.', '_')}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.seek(0)
            file.save(filepath)
            
            try:
                selected_style = request.form.get('style', 'classic_cartoon')
                print(f"DEBUG: Selected cartoonization style: {selected_style}")
                print(f"DEBUG: Available styles: {list(get_available_styles().keys())}")
                
                # Apply cartoonization using the selected style
                cartoon_image = apply_cartoonization(filepath, selected_style)
                print(f"DEBUG: Cartoonization applied, image size: {cartoon_image.size}")
                # Convert processed image to highest quality format for frontend display
                cartoon_buffer = io.BytesIO()
                # Use JPEG with maximum quality for better web display
                if cartoon_image.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for JPEG compatibility
                    rgb_cartoon = Image.new('RGB', cartoon_image.size, (255, 255, 255))
                    rgb_cartoon.paste(cartoon_image, mask=cartoon_image.split()[-1] if cartoon_image.mode == 'RGBA' else None)
                    rgb_cartoon.save(cartoon_buffer, format='JPEG', quality=100, optimize=False)
                else:
                    cartoon_image.save(cartoon_buffer, format='JPEG', quality=100, optimize=False)
                cartoon_buffer.seek(0)
                cartoon_base64 = base64.b64encode(cartoon_buffer.read()).decode()
                
                cartoon_filename = f"cartoon_{selected_style}_{filename}"
                cartoon_filepath = os.path.join(UPLOAD_FOLDER, cartoon_filename)
                # Save with high quality to preserve chosen style
                cartoon_image.save(cartoon_filepath, format='JPEG', quality=95, optimize=True)
                
                styles = get_available_styles()
                style_name = styles.get(selected_style, selected_style.replace('_', ' ').title())
                try:
                    user_profile = get_user_profile(conn, session['user_email'])
                    if user_profile:
                        cartoon_file_size_mb = os.path.getsize(cartoon_filepath) / (1024 * 1024)
                        cartoon_width, cartoon_height = cartoon_image.size
                        
                        image_id = add_cartoonized_image(
                            conn=conn,
                            user_id=user_profile['id'],
                            original_filename=file.filename,
                            cartoon_filename=cartoon_filename,
                            original_file_path=filepath,
                            cartoon_file_path=cartoon_filepath,
                            style_used=selected_style,
                            style_name=style_name,
                            image_width=cartoon_width,
                            image_height=cartoon_height,
                            file_size_mb=round(cartoon_file_size_mb, 2),
                            format_type=format_type
                        )
                        
                        if image_id:
                            print(f"SUCCESS: Cartoonized image saved to database with ID: {image_id}")
                        else:
                            print("WARNING: Failed to save image to database")
                            image_id = None
                except Exception as db_error:
                    print(f"WARNING: Database save error: {db_error}")
                    image_id = None
                
                # Get dynamic pricing for the selected style
                style_price = get_price_for_style(selected_style)
                style_info = get_style_display_info(selected_style)
                
                from dynamic_pricing import get_all_styles_with_pricing
                styles_with_pricing = get_all_styles_with_pricing()
                
                return render_template('toonify.html', user_email=session['user_email'], 
                                     message=f'Image cartoonized successfully using {style_name} style! Size: {file_size_mb:.1f} MB, Dimensions: {width}x{height}, Format: {format_type}', 
                                     message_type='success',
                                     uploaded_image=img_base64,
                                     cartoon_image=cartoon_base64,
                                     selected_style=selected_style,
                                     style_name=style_name,
                                     available_styles=styles,
                                     styles_with_pricing=styles_with_pricing,
                                     image_info={'size_mb': file_size_mb, 'width': width, 'height': height, 'format': format_type},
                                     image_id=image_id,
                                     cartoon_filename=cartoon_filename,
                                     style_price=style_price,
                                     style_info=style_info,
                                     session=session)
                                     
            except Exception as e:
                styles = get_available_styles()
                return render_template('toonify.html', user_email=session['user_email'], 
                                     message=f'Image uploaded but cartoonization failed: {str(e)}', 
                                     message_type='warning',
                                     uploaded_image=img_base64,
                                     available_styles=styles,
                                     image_info={'size_mb': file_size_mb, 'width': width, 'height': height, 'format': format_type}, 
                                     session=session)
        except Exception as e:
            styles = get_available_styles()
            return render_template('toonify.html', user_email=session['user_email'], 
                                 message=f'Error processing image: {str(e)}', message_type='error', 
                                 available_styles=styles, session=session)
    else:
        styles = get_available_styles()
        return render_template('toonify.html', user_email=session['user_email'], 
                             message='Invalid file type. Please upload an image.', message_type='error', 
                             available_styles=styles, session=session)

def handle_reprocess_image():
    """Handle reprocessing existing image with different style"""
    try:
        selected_style = request.form.get('style', 'classic_cartoon')
        print(f"DEBUG REPROCESS: Selected style: {selected_style}")
        user_prefix = f"uploaded_{session['user_email'].replace('@', '_').replace('.', '_')}"
        uploaded_files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(user_prefix) and not filename.startswith('cartoon_'):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                uploaded_files.append((filename, os.path.getmtime(file_path)))
        
        if not uploaded_files:
            styles = get_available_styles()
            return render_template('toonify.html', user_email=session['user_email'], 
                                 message='No previous image found. Please upload a new image.', 
                                 message_type='error', available_styles=styles, session=session)
        
        # Get the most recent uploaded file
        latest_file = max(uploaded_files, key=lambda x: x[1])[0]
        filepath = os.path.join(UPLOAD_FOLDER, latest_file)
        
        # Load and process the existing image
        image = Image.open(filepath)
        width, height = image.size
        format_type = image.format
        
        # Convert original image to base64 for display with highest quality
        img_buffer = io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for JPEG compatibility
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            rgb_image.save(img_buffer, format='JPEG', quality=100, optimize=False)
        else:
            image.save(img_buffer, format='JPEG', quality=100, optimize=False)
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        # Apply cartoonization using the selected style
        cartoon_image = apply_cartoonization(filepath, selected_style)
        
        cartoon_buffer = io.BytesIO()
        if cartoon_image.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for JPEG compatibility
            rgb_cartoon = Image.new('RGB', cartoon_image.size, (255, 255, 255))
            rgb_cartoon.paste(cartoon_image, mask=cartoon_image.split()[-1] if cartoon_image.mode == 'RGBA' else None)
            rgb_cartoon.save(cartoon_buffer, format='JPEG', quality=100, optimize=False)
        else:
            cartoon_image.save(cartoon_buffer, format='JPEG', quality=100, optimize=False)
        cartoon_buffer.seek(0)
        cartoon_base64 = base64.b64encode(cartoon_buffer.read()).decode()
        
        cartoon_filename = f"cartoon_{selected_style}_{latest_file}"
        cartoon_filepath = os.path.join(UPLOAD_FOLDER, cartoon_filename)
        # Save with high quality to preserve chosen style
        cartoon_image.save(cartoon_filepath, format='JPEG', quality=95, optimize=True)
        
        styles = get_available_styles()
        style_name = styles.get(selected_style, selected_style.replace('_', ' ').title())
        try:
            user_profile = get_user_profile(conn, session['user_email'])
            if user_profile:
                cartoon_file_size_mb = os.path.getsize(cartoon_filepath) / (1024 * 1024)
                cartoon_width, cartoon_height = cartoon_image.size
                
                image_id = add_cartoonized_image(
                    conn=conn,
                    user_id=user_profile['id'],
                    original_filename=latest_file,
                    cartoon_filename=cartoon_filename,
                    original_file_path=filepath,
                    cartoon_file_path=cartoon_filepath,
                    style_used=selected_style,
                    style_name=style_name,
                    image_width=cartoon_width,
                    image_height=cartoon_height,
                    file_size_mb=round(cartoon_file_size_mb, 2),
                    format_type=format_type
                )
                
                if image_id:
                    print(f"SUCCESS: Reprocessed image saved to database with ID: {image_id}")
                else:
                    print("WARNING: Failed to save reprocessed image to database")
                    image_id = None
        except Exception as db_error:
            print(f"WARNING: Database save error during reprocessing: {db_error}")
            image_id = None
        
        # Get dynamic pricing for the reprocessed style
        style_price = get_price_for_style(selected_style)
        style_info = get_style_display_info(selected_style)
        
        from dynamic_pricing import get_all_styles_with_pricing
        styles_with_pricing = get_all_styles_with_pricing()
        
        return render_template('toonify.html', user_email=session['user_email'], 
                             message=f'Image reprocessed successfully using {style_name} style!', 
                             message_type='success',
                             uploaded_image=img_base64,
                             cartoon_image=cartoon_base64,
                             selected_style=selected_style,
                             style_name=style_name,
                             available_styles=styles,
                             styles_with_pricing=styles_with_pricing,
                             image_info={'size_mb': file_size_mb, 'width': width, 'height': height, 'format': format_type}, 
                             image_id=image_id,
                             cartoon_filename=cartoon_filename,
                             style_price=style_price,
                             style_info=style_info,
                             session=session)
        
    except Exception as e:
        styles = get_available_styles()
        return render_template('toonify.html', user_email=session['user_email'], 
                             message=f'Error reprocessing image: {str(e)}', 
                             message_type='error', available_styles=styles, session=session)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    print("✅ All cartoon styles ready to use!")
    app.run(debug=True)