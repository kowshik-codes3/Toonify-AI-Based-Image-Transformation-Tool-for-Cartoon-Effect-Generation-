<<<<<<< HEAD


import psycopg2
from database import create_connection
import sys

def view_database():
    """View all users in the database with all fields."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cur:
            # Get table structure first
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns_info = cur.fetchall()
            
            print("🔍 DATABASE SCHEMA - Users Table")
            print("=" * 80)
            print(f"{'Column Name':<20} {'Data Type':<25} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)
            for col in columns_info:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = str(col[3]) if col[3] else "None"
                print(f"{col[0]:<20} {col[1]:<25} {nullable:<10} {default:<15}")
            print()
            
            # Get all user data
            cur.execute("SELECT * FROM users ORDER BY id;")
            users = cur.fetchall()
            
            if not users:
                print("📭 No users found in the database.")
                return True
            
            # Get column names for headers
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            column_names = [row[0] for row in cur.fetchall()]
            
            print("👥 ALL USERS DATA")
            print("=" * 120)
            print(f"📊 Total Users: {len(users)}")
            print()
            
            # Print column headers
            header_format = ""
            for i, col in enumerate(column_names):
                if col == 'hashed_password':
                    width = 15
                elif col == 'email':
                    width = 25
                elif col == 'username':
                    width = 15
                elif col == 'date_of_birth':
                    width = 12
                else:
                    width = 10
                header_format += f"{col:<{width}} "
            print(header_format)
            print("-" * 120)
            
            # Print user data
            for user in users:
                row_format = ""
                for i, value in enumerate(user):
                    col_name = column_names[i]
                    if col_name == 'hashed_password':
                        display_value = "[HIDDEN]"
                        width = 15
                    elif col_name == 'email':
                        display_value = str(value)
                        width = 25
                    elif col_name == 'username':
                        display_value = str(value)
                        width = 15
                    elif col_name == 'date_of_birth':
                        display_value = str(value)
                        width = 12
                    else:
                        display_value = str(value)
                        width = 10
                    row_format += f"{display_value:<{width}} "
                print(row_format)
            
            print("\n" + "=" * 120)
            print("✅ Database view completed successfully!")
            
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def view_database_basic(conn):
    """Basic database view without tabulate formatting."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY id;")
            users = cur.fetchall()
            
            # Get column names
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            column_names = [row[0] for row in cur.fetchall()]
            
            print("👥 ALL USERS DATA")
            print("=" * 80)
            print(f"Columns: {', '.join(column_names)}")
            print("-" * 80)
            
            if not users:
                print("📭 No users found in the database.")
                return True
            
            for i, user in enumerate(users, 1):
                print(f"\n👤 User #{i}:")
                for col_name, value in zip(column_names, user):
                    if col_name == 'hashed_password':
                        print(f"  {col_name}: [HIDDEN - Password Hash]")
                    else:
                        print(f"  {col_name}: {value}")
                print("-" * 40)
            
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False

def interactive_menu():
    """Interactive menu for database operations."""
    while True:
        print("\n" + "="*50)
        print("🗄️  DATABASE VIEWER MENU")
        print("="*50)
        print("1. 👥 View All Users")
        print("2. 📋 View Table Schema")
        print("3. 📊 Database Statistics")
        print("4. 🚪 Exit")
        print("="*50)
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            view_database()
        elif choice == '2':
            view_schema_only()
        elif choice == '3':
            view_statistics()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

def view_schema_only():
    """View only the database schema."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns_info = cur.fetchall()
            
            print("\n🔍 DATABASE SCHEMA - Users Table")
            print("=" * 60)
            
            for col in columns_info:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = col[3] if col[3] else "None"
                print(f"📝 {col[0]}: {col[1]} (Nullable: {nullable}, Default: {default})")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

def view_statistics():
    """View database statistics."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            total_users = cur.fetchone()[0]
            
            cur.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender;")
            gender_stats = cur.fetchall()
        
            cur.execute("SELECT MIN(age), MAX(age), AVG(age) FROM users;")
            age_stats = cur.fetchone()
            
            print("\n📊 DATABASE STATISTICS")
            print("=" * 40)
            print(f"👥 Total Users: {total_users}")
            
            if total_users > 0:
                print(f"🎂 Age Range: {age_stats[0]} - {age_stats[1]} years")
                print(f"📈 Average Age: {age_stats[2]:.1f} years")
                
                print("\n⚧ Gender Distribution:")
                for gender, count in gender_stats:
                    percentage = (count / total_users) * 100
                    print(f"  {gender.title()}: {count} ({percentage:.1f}%)")
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🗄️  Welcome to Toonify Database Viewer!")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        view_database()
    else:
=======


import psycopg2
from database import create_connection
import sys

def view_database():
    """View all users in the database with all fields."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return False
    
    try:
        with conn.cursor() as cur:
            # Get table structure first
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns_info = cur.fetchall()
            
            print("🔍 DATABASE SCHEMA - Users Table")
            print("=" * 80)
            print(f"{'Column Name':<20} {'Data Type':<25} {'Nullable':<10} {'Default':<15}")
            print("-" * 80)
            for col in columns_info:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = str(col[3]) if col[3] else "None"
                print(f"{col[0]:<20} {col[1]:<25} {nullable:<10} {default:<15}")
            print()
            
            # Get all user data
            cur.execute("SELECT * FROM users ORDER BY id;")
            users = cur.fetchall()
            
            if not users:
                print("📭 No users found in the database.")
                return True
            
            # Get column names for headers
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            column_names = [row[0] for row in cur.fetchall()]
            
            print("👥 ALL USERS DATA")
            print("=" * 120)
            print(f"📊 Total Users: {len(users)}")
            print()
            
            # Print column headers
            header_format = ""
            for i, col in enumerate(column_names):
                if col == 'hashed_password':
                    width = 15
                elif col == 'email':
                    width = 25
                elif col == 'username':
                    width = 15
                elif col == 'date_of_birth':
                    width = 12
                else:
                    width = 10
                header_format += f"{col:<{width}} "
            print(header_format)
            print("-" * 120)
            
            # Print user data
            for user in users:
                row_format = ""
                for i, value in enumerate(user):
                    col_name = column_names[i]
                    if col_name == 'hashed_password':
                        display_value = "[HIDDEN]"
                        width = 15
                    elif col_name == 'email':
                        display_value = str(value)
                        width = 25
                    elif col_name == 'username':
                        display_value = str(value)
                        width = 15
                    elif col_name == 'date_of_birth':
                        display_value = str(value)
                        width = 12
                    else:
                        display_value = str(value)
                        width = 10
                    row_format += f"{display_value:<{width}} "
                print(row_format)
            
            print("\n" + "=" * 120)
            print("✅ Database view completed successfully!")
            
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def view_database_basic(conn):
    """Basic database view without tabulate formatting."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY id;")
            users = cur.fetchall()
            
            # Get column names
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            column_names = [row[0] for row in cur.fetchall()]
            
            print("👥 ALL USERS DATA")
            print("=" * 80)
            print(f"Columns: {', '.join(column_names)}")
            print("-" * 80)
            
            if not users:
                print("📭 No users found in the database.")
                return True
            
            for i, user in enumerate(users, 1):
                print(f"\n👤 User #{i}:")
                for col_name, value in zip(column_names, user):
                    if col_name == 'hashed_password':
                        print(f"  {col_name}: [HIDDEN - Password Hash]")
                    else:
                        print(f"  {col_name}: {value}")
                print("-" * 40)
            
            return True
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False

def interactive_menu():
    """Interactive menu for database operations."""
    while True:
        print("\n" + "="*50)
        print("🗄️  DATABASE VIEWER MENU")
        print("="*50)
        print("1. 👥 View All Users")
        print("2. 📋 View Table Schema")
        print("3. 📊 Database Statistics")
        print("4. 🚪 Exit")
        print("="*50)
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            view_database()
        elif choice == '2':
            view_schema_only()
        elif choice == '3':
            view_statistics()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

def view_schema_only():
    """View only the database schema."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """)
            columns_info = cur.fetchall()
            
            print("\n🔍 DATABASE SCHEMA - Users Table")
            print("=" * 60)
            
            for col in columns_info:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = col[3] if col[3] else "None"
                print(f"📝 {col[0]}: {col[1]} (Nullable: {nullable}, Default: {default})")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

def view_statistics():
    """View database statistics."""
    conn = create_connection()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            total_users = cur.fetchone()[0]
            
            cur.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender;")
            gender_stats = cur.fetchall()
        
            cur.execute("SELECT MIN(age), MAX(age), AVG(age) FROM users;")
            age_stats = cur.fetchone()
            
            print("\n📊 DATABASE STATISTICS")
            print("=" * 40)
            print(f"👥 Total Users: {total_users}")
            
            if total_users > 0:
                print(f"🎂 Age Range: {age_stats[0]} - {age_stats[1]} years")
                print(f"📈 Average Age: {age_stats[2]:.1f} years")
                
                print("\n⚧ Gender Distribution:")
                for gender, count in gender_stats:
                    percentage = (count / total_users) * 100
                    print(f"  {gender.title()}: {count} ({percentage:.1f}%)")
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🗄️  Welcome to Toonify Database Viewer!")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        view_database()
    else:
>>>>>>> b9aeece1db44d5c9240ec23dcfbd048d90b6ab50
        interactive_menu()