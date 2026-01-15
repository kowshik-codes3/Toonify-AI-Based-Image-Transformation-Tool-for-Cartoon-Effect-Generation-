import psycopg2
import os
import sys


def create_connection():
    """Create a database connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "Kowshik.v@321"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432")
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        return None



def create_users_table(conn):
    """Create the users table if it does not exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    hashed_password BYTEA NOT NULL,
                    date_of_birth DATE NOT NULL,
                    age INTEGER NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    security_question TEXT NOT NULL,
                    security_answer_hash BYTEA NOT NULL
                );
            """)
            conn.commit()
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")


def add_user(conn, username, email, hashed_password, date_of_birth, age, gender, security_question, security_answer_hash):
    """Add a new user to the users table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, hashed_password, date_of_birth, age, gender, security_question, security_answer_hash) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (username, email, hashed_password, date_of_birth, age, gender, security_question, security_answer_hash)
            )
            conn.commit()
    except psycopg2.Error as e:
        print(f"Error adding user: {e}")

def get_user(conn, email):
    """Retrieve a user by email."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()
    except psycopg2.Error as e:
        print(f"Error getting user: {e}")
        return None

def get_user_by_username(conn, username):
    """Retrieve a user by username."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cur.fetchone()
    except psycopg2.Error as e:
        print(f"Error getting user by username: {e}")
        return None

def check_user_exists(conn, username, email):
    """Check if user with username or email already exists."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            return cur.fetchone() is not None
    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return True  # Return True to prevent signup on error

def check_user_exists_exclude_current(conn, username, email, current_user_id):
    """Check if user with username or email already exists, excluding current user."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s", 
                (username, email, current_user_id)
            )
            return cur.fetchone() is not None
    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return True  # Return True to prevent update on error

def update_user_profile(conn, user_id, username, email, date_of_birth, age, gender, security_question, security_answer_hash=None):
    """Update user profile information."""
    try:
        with conn.cursor() as cur:
            if security_answer_hash:
                # Update with new security answer
                cur.execute("""
                    UPDATE users 
                    SET username = %s, email = %s, date_of_birth = %s, age = %s, 
                        gender = %s, security_question = %s, security_answer_hash = %s
                    WHERE id = %s
                """, (username, email, date_of_birth, age, gender, security_question, security_answer_hash, user_id))
            else:
                # Update without changing security answer
                cur.execute("""
                    UPDATE users 
                    SET username = %s, email = %s, date_of_birth = %s, age = %s, 
                        gender = %s, security_question = %s
                    WHERE id = %s
                """, (username, email, date_of_birth, age, gender, security_question, user_id))
            
            conn.commit()
            return cur.rowcount > 0
    except psycopg2.Error as e:
        print(f"Error updating user profile: {e}")
        conn.rollback()
        return False

def get_user_profile(conn, email):
    """Get complete user profile data by email."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, date_of_birth, age, gender, security_question FROM users WHERE email = %s", 
                (email,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'date_of_birth': row[3],
                    'age': row[4],
                    'gender': row[5],
                    'security_question': row[6],
                    'created_at': None  # We can add this field later if needed
                }
            return None
    except psycopg2.Error as e:
        print(f"Error getting user profile: {e}")
        return None

def migrate_database_schema():
    """Migrate the database to include new user fields."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name IN ('username', 'date_of_birth', 'age', 'gender', 'security_question', 'security_answer_hash');
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            
            basic_fields = {'username', 'date_of_birth', 'age', 'gender'}
            security_fields = {'security_question', 'security_answer_hash'}
            
            has_basic = basic_fields.issubset(set(existing_columns))
            has_security = security_fields.issubset(set(existing_columns))
            
            if has_basic and has_security:
                print("✅ Database is already up to date!")
                return True
            
            print("🔄 Database migration needed...")
            
            if not has_basic:
                print("📝 Basic user fields (username, age, gender, DOB) will be added")
            if not has_security:
                print("🔒 Security question fields will be added")
            
            print("\n⚠️  WARNING: This will recreate the users table and delete all existing data!")
            print("📋 New schema will include:")
            print("   - id (SERIAL PRIMARY KEY)")
            print("   - username (VARCHAR(50), UNIQUE, NOT NULL)")
            print("   - email (VARCHAR(120), UNIQUE, NOT NULL)")
            print("   - hashed_password (BYTEA, NOT NULL)")
            print("   - date_of_birth (DATE, NOT NULL)")
            print("   - age (INTEGER, NOT NULL)")
            print("   - gender (VARCHAR(20), NOT NULL)")
            print("   - security_question (TEXT, NOT NULL)")
            print("   - security_answer_hash (BYTEA, NOT NULL)")
            
            response = input("\nDo you want to continue? (yes/no): ").lower().strip()
            if response not in ['yes', 'y']:
                print("Migration cancelled.")
                return False
            
            print("\n🔄 Migrating database...")
            
            cur.execute("DROP TABLE IF EXISTS users CASCADE;")
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    hashed_password BYTEA NOT NULL,
                    date_of_birth DATE NOT NULL,
                    age INTEGER NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    security_question TEXT NOT NULL,
                    security_answer_hash BYTEA NOT NULL
                );
            """)
            
            # Create cartoonized_images table
            print("🖼️  Creating cartoonized images table...")
            create_cartoonized_images_table(conn)
            
            # Create feedback table
            print("💭 Creating feedback table...")
            create_feedback_table(conn)
            
            conn.commit()
            print("✅ Database migration completed successfully!")
            print("📝 All user fields have been added including security questions")
            print("🖼️  Cartoonized images table created for storing user artwork")
            print("💭 Feedback table created for user experience tracking")
            print("⚠️  All existing user accounts have been deleted due to schema changes.")
            print("👤 Users will need to create new accounts with the enhanced signup form.")
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_database_schema():
    """Verify the current database schema."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cur:
            # Check if users table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                print("⚠️  Users table does not exist")
                return False
            
            # Get table structure
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns = cur.fetchall()
            
            # Get user count
            cur.execute("SELECT COUNT(*) FROM users;")
            user_count = cur.fetchone()[0]
            
            print("📋 Current Database Schema:")
            print("=" * 80)
            print(f"{'Column':<25} {'Type':<20} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)
            
            for col in columns:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = str(col[3]) if col[3] else "None"
                if len(default) > 15:
                    default = default[:12] + "..."
                print(f"{col[0]:<25} {col[1]:<20} {nullable:<10} {default:<15}")
            
            print(f"\n👥 Total Users: {user_count}")
            
            # Check for required fields
            column_names = [col[0] for col in columns]
            required_fields = ['id', 'username', 'email', 'hashed_password', 'date_of_birth', 'age', 'gender', 'security_question', 'security_answer_hash']
            missing_fields = [field for field in required_fields if field not in column_names]
            
            if missing_fields:
                print(f"\n⚠️  Missing required fields: {', '.join(missing_fields)}")
                print("🔧 Run migrate_database_schema() to update the database")
                return False
            else:
                print("\n✅ Database schema is complete and up to date!")
                return True
            
    except psycopg2.Error as e:
        print(f"❌ Schema verification failed: {e}")
        return False
    finally:
        conn.close()

def reset_database():
    """Reset the database by dropping and recreating the users table."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    print("🚨 DATABASE RESET WARNING")
    print("=" * 50)
    print("This will completely delete all user data and recreate the users table.")
    print("This action cannot be undone!")
    
    response = input("\nAre you sure you want to reset the database? (type 'RESET' to confirm): ").strip()
    if response != 'RESET':
        print("Database reset cancelled.")
        return False
    
    try:
        with conn.cursor() as cur:
            print("\n🔄 Resetting database...")
            
            # Drop existing tables (CASCADE will handle foreign key dependencies)
            cur.execute("DROP TABLE IF EXISTS cartoonized_images CASCADE;")
            cur.execute("DROP TABLE IF EXISTS users CASCADE;")
            
            # Recreate table with current schema
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    hashed_password BYTEA NOT NULL,
                    date_of_birth DATE NOT NULL,
                    age INTEGER NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    security_question TEXT NOT NULL,
                    security_answer_hash BYTEA NOT NULL
                );
            """)
            
            # Create cartoonized_images table
            print("🖼️  Creating cartoonized images table...")
            create_cartoonized_images_table(conn)
            
            # Create feedback table
            print("💭 Creating feedback table...")
            create_feedback_table(conn)
            
            conn.commit()
            print("✅ Database reset completed successfully!")
            print("🗃️  Empty users table created with full schema")
            print("🖼️  Cartoonized images table created for storing user artwork")
            print("💭 Feedback table created for user experience tracking")
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Database reset failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def run_migration_cli():
    """Interactive command-line interface for database migrations."""
    print("🗄️  Toonify Database Migration Tool")
    print("=" * 50)
    
    while True:
        print("\nAvailable Operations:")
        print("1. 📋 Verify Database Schema")
        print("2. 🔄 Migrate Database Schema")
        print("3. 🚨 Reset Database (DELETE ALL DATA)")
        print("4. 🚪 Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            print("\n" + "="*50)
            verify_database_schema()
        elif choice == '2':
            print("\n" + "="*50)
            migrate_database_schema()
        elif choice == '3':
            print("\n" + "="*50)
            reset_database()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

# =============================================================================
# COMMAND LINE EXECUTION
# =============================================================================

def create_cartoonized_images_table(conn):
    """Create the cartoonized_images table if it does not exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cartoonized_images (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    original_filename VARCHAR(255) NOT NULL,
                    cartoon_filename VARCHAR(255) NOT NULL,
                    original_file_path TEXT NOT NULL,
                    cartoon_file_path TEXT NOT NULL,
                    style_used VARCHAR(50) NOT NULL,
                    style_name VARCHAR(100) NOT NULL,
                    image_width INTEGER,
                    image_height INTEGER,
                    file_size_mb DECIMAL(10,2),
                    format_type VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create index for faster user queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_cartoonized_images_user_id 
                ON cartoonized_images(user_id);
            """)
            
            # Create index for faster date queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_cartoonized_images_created_at 
                ON cartoonized_images(created_at);
            """)
            
            conn.commit()
            print("Cartoonized images table created successfully!")
    except psycopg2.Error as e:
        print(f"Error creating cartoonized_images table: {e}")

def add_cartoonized_image(conn, user_id, original_filename, cartoon_filename, 
                         original_file_path, cartoon_file_path, style_used, style_name,
                         image_width=None, image_height=None, file_size_mb=None, format_type=None):
    """Add a new cartoonized image record to the database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cartoonized_images 
                (user_id, original_filename, cartoon_filename, original_file_path, 
                 cartoon_file_path, style_used, style_name, image_width, image_height, 
                 file_size_mb, format_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, original_filename, cartoon_filename, original_file_path,
                  cartoon_file_path, style_used, style_name, image_width, image_height,
                  file_size_mb, format_type))
            
            image_id = cur.fetchone()[0]
            conn.commit()
            return image_id
    except psycopg2.Error as e:
        print(f"Error adding cartoonized image: {e}")
        return None

def get_user_cartoonized_images(conn, user_id, limit=20, offset=0):
    """Get cartoonized images for a specific user, ordered by creation date (newest first)."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, original_filename, cartoon_filename, original_file_path,
                       cartoon_file_path, style_used, style_name, image_width, image_height,
                       file_size_mb, format_type, created_at, updated_at, is_paid, payment_id, order_id, payment_date
                FROM cartoonized_images 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            columns = ['id', 'original_filename', 'cartoon_filename', 'original_file_path',
                      'cartoon_file_path', 'style_used', 'style_name', 'image_width', 
                      'image_height', 'file_size_mb', 'format_type', 'created_at', 'updated_at',
                      'is_paid', 'payment_id', 'order_id', 'payment_date']
            
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
    except psycopg2.Error as e:
        print(f"Error getting user cartoonized images: {e}")
        return []

def get_user_paid_cartoonized_images(conn, user_id, limit=20, offset=0):
    """Get only PAID cartoonized images for a specific user, ordered by creation date (newest first)."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, original_filename, cartoon_filename, original_file_path,
                       cartoon_file_path, style_used, style_name, image_width, image_height,
                       file_size_mb, format_type, created_at, updated_at, is_paid, payment_id, order_id, payment_date
                FROM cartoonized_images 
                WHERE user_id = %s AND is_paid = TRUE
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            columns = ['id', 'original_filename', 'cartoon_filename', 'original_file_path',
                      'cartoon_file_path', 'style_used', 'style_name', 'image_width', 
                      'image_height', 'file_size_mb', 'format_type', 'created_at', 'updated_at',
                      'is_paid', 'payment_id', 'order_id', 'payment_date']
            
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
    except psycopg2.Error as e:
        print(f"Error getting user paid cartoonized images: {e}")
        return []

def get_cartoonized_image_by_id(conn, image_id, user_id):
    """Get a specific cartoonized image by ID, ensuring it belongs to the user."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, original_filename, cartoon_filename, original_file_path,
                       cartoon_file_path, style_used, style_name, image_width, image_height,
                       file_size_mb, format_type, created_at, updated_at
                FROM cartoonized_images 
                WHERE id = %s AND user_id = %s
            """, (image_id, user_id))
            
            row = cur.fetchone()
            if row:
                columns = ['id', 'original_filename', 'cartoon_filename', 'original_file_path',
                          'cartoon_file_path', 'style_used', 'style_name', 'image_width', 
                          'image_height', 'file_size_mb', 'format_type', 'created_at', 'updated_at']
                return dict(zip(columns, row))
            return None
    except psycopg2.Error as e:
        print(f"Error getting cartoonized image by ID: {e}")
        return None

def delete_cartoonized_image(conn, image_id, user_id):
    """Delete a cartoonized image record (files should be deleted separately)."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM cartoonized_images 
                WHERE id = %s AND user_id = %s
                RETURNING cartoon_file_path, original_file_path
            """, (image_id, user_id))
            
            deleted_row = cur.fetchone()
            conn.commit()
            return deleted_row  # Returns file paths for cleanup
    except psycopg2.Error as e:
        print(f"Error deleting cartoonized image: {e}")
        return None

def get_user_images_count(conn, user_id):
    """Get total count of cartoonized images for a user."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM cartoonized_images WHERE user_id = %s", (user_id,))
            return cur.fetchone()[0]
    except psycopg2.Error as e:
        print(f"Error getting user images count: {e}")
        return 0

def get_user_stats(conn, user_id):
    """Get comprehensive user statistics for dashboard."""
    try:
        with conn.cursor() as cur:
            # Get total images count
            cur.execute("SELECT COUNT(*) FROM cartoonized_images WHERE user_id = %s", (user_id,))
            total_images = cur.fetchone()[0]
            
            # Get most used style
            cur.execute("""
                SELECT style_name, COUNT(*) as count 
                FROM cartoonized_images 
                WHERE user_id = %s 
                GROUP BY style_name 
                ORDER BY count DESC 
                LIMIT 1
            """, (user_id,))
            favorite_style_result = cur.fetchone()
            favorite_style = favorite_style_result[0] if favorite_style_result else "None"
            
            # Get total file size processed (in MB)
            cur.execute("SELECT COALESCE(SUM(file_size_mb), 0) FROM cartoonized_images WHERE user_id = %s", (user_id,))
            total_size_mb = float(cur.fetchone()[0])
            
            # Get recent activity (images created in last 30 days)
            cur.execute("""
                SELECT COUNT(*) FROM cartoonized_images 
                WHERE user_id = %s AND created_at >= CURRENT_DATE - INTERVAL '30 days'
            """, (user_id,))
            recent_activity = cur.fetchone()[0]
            
            return {
                'total_images': total_images,
                'favorite_style': favorite_style,
                'total_size_mb': round(total_size_mb, 2),
                'member_since': None,  # Users table doesn't have created_at
                'recent_activity': recent_activity
            }
    except psycopg2.Error as e:
        print(f"Error getting user stats: {e}")
        return {
            'total_images': 0,
            'favorite_style': 'None',
            'total_size_mb': 0.0,
            'member_since': None,
            'recent_activity': 0
        }

def mark_image_as_paid(conn, image_id, payment_id, order_id):
    """Mark an image as paid with payment details."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE cartoonized_images 
                SET is_paid = TRUE, payment_id = %s, order_id = %s, payment_date = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (payment_id, order_id, image_id))
            conn.commit()
            return cur.rowcount > 0
    except psycopg2.Error as e:
        print(f"Error marking image as paid: {e}")
        conn.rollback()
        return False

def is_image_paid(conn, image_id, user_id):
    """Check if an image has been paid for by the user."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT is_paid FROM cartoonized_images 
                WHERE id = %s AND user_id = %s
            """, (image_id, user_id))
            result = cur.fetchone()
            return result and result[0] if result else False
    except psycopg2.Error as e:
        print(f"Error checking payment status: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'migrate':
            migrate_database_schema()
        elif command == 'verify':
            verify_database_schema()
        elif command == 'reset':
            reset_database()
        else:
            print("Usage: python database.py [migrate|verify|reset]")
    else:
        run_migration_cli()


def create_feedback_table(conn):
    """Create the feedback table if it does not exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    image_filename VARCHAR(255) NOT NULL,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5) NOT NULL,
                    feedback_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, image_filename)
                );
            """)
            
            # Create indexes for better performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_user_id 
                ON user_feedback(user_id);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_image_filename 
                ON user_feedback(image_filename);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_rating 
                ON user_feedback(rating);
            """)
            
            conn.commit()
    except psycopg2.Error as e:
        print(f"Error creating feedback table: {e}")


def add_user_feedback(conn, user_id, image_filename, rating, feedback_text):
    """Add user feedback for an image."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_feedback (user_id, image_filename, rating, feedback_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, image_filename) 
                DO UPDATE SET 
                    rating = EXCLUDED.rating,
                    feedback_text = EXCLUDED.feedback_text,
                    created_at = CURRENT_TIMESTAMP
                RETURNING id;
            """, (user_id, image_filename, rating, feedback_text))
            
            feedback_id = cur.fetchone()[0]
            conn.commit()
            return feedback_id
    except psycopg2.Error as e:
        print(f"Error adding user feedback: {e}")
        return None


def get_user_feedback(conn, user_id, image_filename):
    """Get user feedback for a specific image."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, rating, feedback_text, created_at
                FROM user_feedback 
                WHERE user_id = %s AND image_filename = %s
            """, (user_id, image_filename))
            
            result = cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'rating': result[1],
                    'feedback_text': result[2],
                    'created_at': result[3]
                }
            return None
    except psycopg2.Error as e:
        print(f"Error getting user feedback: {e}")
        return None


def get_feedback_statistics(conn):
    """Get overall feedback statistics."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating::DECIMAL) as average_rating,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
                FROM user_feedback
            """)
            
            result = cur.fetchone()
            if result:
                return {
                    'total_feedback': result[0],
                    'average_rating': float(result[1]) if result[1] else 0,
                    'five_star': result[2],
                    'four_star': result[3],
                    'three_star': result[4],
                    'two_star': result[5],
                    'one_star': result[6]
                }
            return None
    except psycopg2.Error as e:
        print(f"Error getting feedback statistics: {e}")
        return None


def has_user_given_feedback(conn, user_id, image_filename):
    """Check if user has already given feedback for an image."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM user_feedback 
                    WHERE user_id = %s AND image_filename = %s
                )
            """, (user_id, image_filename))
            
            return cur.fetchone()[0]
    except psycopg2.Error as e:
        print(f"Error checking user feedback: {e}")
        return False


def get_gallery_analytics(conn):
    """Get comprehensive analytics for the gallery page."""
    try:
        analytics = {}
        
        with conn.cursor() as cur:
            # Total transformations created
            cur.execute("SELECT COUNT(*) FROM cartoonized_images")
            analytics['total_transformations'] = cur.fetchone()[0]
            
            # Total users
            cur.execute("SELECT COUNT(*) FROM users")
            analytics['total_users'] = cur.fetchone()[0]
            
            # Feedback statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating::DECIMAL) as average_rating,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
                FROM user_feedback
            """)
            
            feedback_result = cur.fetchone()
            if feedback_result:
                analytics.update({
                    'total_feedback': feedback_result[0],
                    'average_rating': float(feedback_result[1]) if feedback_result[1] else 0,
                    'five_star': feedback_result[2],
                    'four_star': feedback_result[3],
                    'three_star': feedback_result[4],
                    'two_star': feedback_result[5],
                    'one_star': feedback_result[6]
                })
            
            # Recent feedback count (last 30 days)
            cur.execute("""
                SELECT COUNT(*) 
                FROM user_feedback 
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)
            analytics['recent_feedback'] = cur.fetchone()[0]
            
            # Satisfaction rate (4-5 star ratings)
            if analytics.get('total_feedback', 0) > 0:
                satisfaction_count = analytics.get('five_star', 0) + analytics.get('four_star', 0)
                analytics['satisfaction_rate'] = (satisfaction_count / analytics['total_feedback']) * 100
            else:
                analytics['satisfaction_rate'] = 0
            
            return analytics
            
    except psycopg2.Error as e:
        print(f"Error getting gallery analytics: {e}")
        return {
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
