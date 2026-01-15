#!/usr/bin/env python3
"""
Sample Data Generator for Feedback Analytics
Populates the database with sample feedback data to demonstrate analytics
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

import database

def create_sample_feedback():
    """Create sample feedback data for analytics demonstration"""
    conn = database.create_connection()
    if not conn:
        print("❌ Could not connect to database")
        return
    
    try:
        # Sample feedback texts
        feedback_texts = [
            "Amazing transformation! The quality is incredible and the style looks professional.",
            "Love how my photo turned into a cartoon. The Disney style is my favorite!",
            "Quick processing and great results. Will definitely use again!",
            "The anime style transformation exceeded my expectations. Highly recommend!",
            "Good service but could use more style options. Overall satisfied.",
            "Perfect for social media posts. The cartoon effect is so realistic!",
            "Easy to use interface and fast results. Great job!",
            "The pencil sketch style is beautiful. Thanks for this amazing tool!",
            "Impressive AI technology. The transformations are high quality.",
            "Fun to use and creates great artwork from regular photos.",
        ]
        
        # Sample ratings distribution (weighted towards positive)
        ratings_pool = [5, 5, 5, 5, 4, 4, 4, 3, 2, 1]
        
        # Create sample feedback entries
        sample_count = 50
        created_count = 0
        
        for i in range(sample_count):
            try:
                user_id = random.randint(1, 3)  # Using existing user IDs 1, 2, 3
                image_filename = f"cartoon_sample_{random.randint(1, 20)}.jpg"  # Sample image filenames
                rating = random.choice(ratings_pool)
                feedback_text = random.choice(feedback_texts)
                
                # Add some variation in feedback text
                if random.random() < 0.3:  # 30% chance of no text feedback
                    feedback_text = None
                
                result = database.add_user_feedback(conn, user_id, image_filename, rating, feedback_text)
                if result:
                    created_count += 1
                    print(f"✅ Created feedback {created_count}/{sample_count}")
                
            except Exception as e:
                print(f"⚠️ Skipped duplicate feedback (user {user_id}, image {image_filename})")
                continue
        
        print(f"\n🎉 Successfully created {created_count} sample feedback entries!")
        
        # Display analytics
        analytics = database.get_gallery_analytics(conn)
        print("\n📊 Current Analytics:")
        print(f"Total Feedback: {analytics['total_feedback']}")
        print(f"Average Rating: {analytics['average_rating']:.1f}/5.0")
        print(f"Satisfaction Rate: {analytics['satisfaction_rate']:.1f}%")
        print(f"Rating Distribution:")
        print(f"  ⭐⭐⭐⭐⭐ (5 stars): {analytics['five_star']}")
        print(f"  ⭐⭐⭐⭐ (4 stars): {analytics['four_star']}")
        print(f"  ⭐⭐⭐ (3 stars): {analytics['three_star']}")
        print(f"  ⭐⭐ (2 stars): {analytics['two_star']}")
        print(f"  ⭐ (1 star): {analytics['one_star']}")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Creating sample feedback data for analytics...")
    create_sample_feedback()