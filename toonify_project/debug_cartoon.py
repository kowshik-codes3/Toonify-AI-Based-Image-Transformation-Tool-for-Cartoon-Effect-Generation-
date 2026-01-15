#!/usr/bin/env python3
"""
Quick test for classic cartoon debugging
"""
import os
import sys
from PIL import Image

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from cartoonization import classic_cartoon, classic_cartoon_opencv
    
    # Find a test image
    uploads_dir = "uploads"
    test_image = None
    
    for file in os.listdir(uploads_dir):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            test_image = os.path.join(uploads_dir, file)
            break
    
    if test_image:
        print(f"🧪 Testing classic cartoon with: {test_image}")
        print("=" * 50)
        
        # Test OpenCV version directly
        print("📝 Testing OpenCV classic cartoon...")
        try:
            opencv_result = classic_cartoon_opencv(test_image)
            if opencv_result:
                print("✅ OpenCV classic cartoon works!")
                opencv_result.save("test_opencv_cartoon.jpg")
                print("💾 Saved as: test_opencv_cartoon.jpg")
            else:
                print("❌ OpenCV classic cartoon failed")
        except Exception as e:
            print(f"❌ OpenCV classic cartoon error: {e}")
        
        print("\n" + "=" * 50)
        
        # Test full classic cartoon function
        print("📝 Testing full classic_cartoon function...")
        try:
            result = classic_cartoon(test_image)
            if result:
                print("✅ Classic cartoon function works!")
                result.save("test_full_cartoon.jpg")
                print("💾 Saved as: test_full_cartoon.jpg")
                
                # Compare if it's different from original
                original = Image.open(test_image)
                if original.size != result.size or original.mode != result.mode:
                    print("✅ Result is different from original (good!)")
                else:
                    print("⚠️ Result might be same as original (check files)")
            else:
                print("❌ Classic cartoon function returned None")
        except Exception as e:
            print(f"❌ Classic cartoon function error: {e}")
    
    else:
        print("❌ No test image found in uploads folder")

except Exception as e:
    print(f"❌ Import or setup error: {e}")
    import traceback
    traceback.print_exc()