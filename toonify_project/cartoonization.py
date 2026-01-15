import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import os
from tkinter.filedialog import *

def vintage_style(image_path):
    """
    Convert an image to vintage grayscale style like old photographs
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Error: Image not found or path is incorrect.")
    
    # Convert to PIL for easier processing
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)
    
    # Step 1: Convert to grayscale
    gray_img = img_pil.convert('L')
    
    # Step 2: Apply sepia tone effect (convert back to RGB first)
    sepia_img = gray_img.convert('RGB')
    
    # Create sepia effect by adjusting RGB channels
    pixels = sepia_img.load()
    width, height = sepia_img.size
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            
            # Sepia formula
            tr = int(0.393 * r + 0.769 * g + 0.189 * b)
            tg = int(0.349 * r + 0.686 * g + 0.168 * b)
            tb = int(0.272 * r + 0.534 * g + 0.131 * b)
            
            # Clamp values to 0-255
            pixels[x, y] = (min(255, tr), min(255, tg), min(255, tb))
    
    # Step 3: Reduce contrast slightly for vintage feel
    contrast_enhancer = ImageEnhance.Contrast(sepia_img)
    vintage_img = contrast_enhancer.enhance(0.85)
    
    # Step 4: Reduce brightness slightly
    brightness_enhancer = ImageEnhance.Brightness(vintage_img)
    vintage_img = brightness_enhancer.enhance(0.9)
    
    # Step 5: Add slight blur for old photo effect
    vintage_img = vintage_img.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    # Step 6: Add vignette effect (darken edges)
    width, height = vintage_img.size
    vignette = Image.new('RGB', (width, height), (0, 0, 0))
    
    # Create radial gradient for vignette
    center_x, center_y = width // 2, height // 2
    max_distance = min(width, height) // 2
    
    vignette_pixels = vignette.load()
    for y in range(height):
        for x in range(width):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            if distance < max_distance:
                alpha = distance / max_distance
                vignette_pixels[x, y] = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
            else:
                vignette_pixels[x, y] = (255, 255, 255)
    
    # Blend vignette with image
    vintage_img = Image.blend(vintage_img, vignette, alpha=0.3)
    
    return vintage_img

def pencil_sketch(image_path):
    """
    Convert an image to pencil sketch style using OpenCV (original implementation)
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Error: Image not found or path is incorrect.")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # reduce noise and smooth image, make cleaner edges
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detect edges using laplacian (you can also try canny)
    edges = cv2.Laplacian(gray_blur, cv2.CV_8U, ksize=5)
    
    # invert the edges to look like pencil outlined
    inverted = cv2.bitwise_not(edges)
    
    # Optional: make it more sketchy (slightly blur)
    sketch = cv2.GaussianBlur(inverted, (3, 3), 0)
    
    # Convert back to RGB for PIL
    sketch_rgb = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)
    
    return Image.fromarray(sketch_rgb)

def oil_painting(image_path):
    """
    Convert an image to oil painting style using OpenCV (original implementation)
    """
    img = Image.open(image_path)
    
    # Step 1: smooth the image to reduce noise
    smooth = img.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Step 2: Detect edges for texture overlay
    edges = smooth.filter(ImageFilter.FIND_EDGES)
    edges_blur = edges.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Step 3: Enhance colors for painterly vibes
    enhancer = ImageEnhance.Color(smooth)
    colored = enhancer.enhance(1.5)
    
    contrast = ImageEnhance.Contrast(colored)
    colored = contrast.enhance(1.2)
    
    brightness = ImageEnhance.Brightness(colored)
    colored = brightness.enhance(1.05)
    
    # Step 4: blend edge texture into colored image
    oil_paint = Image.blend(colored, edges_blur.convert("RGB"), alpha=0.1)
    
    # Step 5: Optional posterize for painting feel
    oil_paint = ImageOps.posterize(oil_paint, bits=5)
    
    # Step 6: Final sharpening to improve clarity
    oil_paint = oil_paint.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    
    return oil_paint

def colored_sketch(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Error: Image not found or path is incorrect.")
    img = cv2.resize(img, (800, int(img.shape[0]*800/img.shape[1])))
    
    # Step 1: smooth the image slightly to remove noise
    img_smooth = cv2.bilateralFilter(img, 9, sigmaColor=70, sigmaSpace=70)
    
    # Step 2: convert to grayscale for edge detection
    gray = cv2.cvtColor(img_smooth, cv2.COLOR_BGR2GRAY)
    
    # Step 3: Detect edges using Laplacian (soft pencil effect)
    edges = cv2.Laplacian(gray, cv2.CV_8U, ksize=5)
    edges_inv = cv2.bitwise_not(edges)  # invert edges to look like sketch
    
    # Step 4: Convert inverted edges to 3 channels
    edges_colored = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)
    
    # Step 5: blend the original image with edges
    colored_sketch = cv2.multiply(img_smooth.astype(float)/255, edges_colored.astype(float)/255)
    colored_sketch = np.clip(colored_sketch*255, 0, 255).astype(np.uint8)
    
    # Convert BGR to RGB for PIL
    colored_sketch_rgb = cv2.cvtColor(colored_sketch, cv2.COLOR_BGR2RGB)
    
    return Image.fromarray(colored_sketch_rgb)

def classic_cartoon(image_path):
    """
    Convert an image to vintage grayscale style like old photographs
    """
    return vintage_style(image_path)

def pixel_art_style(image_path):
    img = Image.open(image_path)
    
    # Resize to small dimensions for pixel art effect
    small_img = img.resize((64, 64), Image.NEAREST)
    
    # Upscale back to original size
    pixel_art = small_img.resize(img.size, Image.NEAREST)
    
    pixel_art.save("pixel_art_image.png")
    
    return pixel_art

def candy_style(image_path):
    img = Image.open(image_path).convert("RGB")
    
    # Step 1: Apply bilateral filter for smooth color regions
    img_array = np.array(img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    for _ in range(3):
        img_bgr = cv2.bilateralFilter(img_bgr, 15, 80, 80)
    
    # Convert back to RGB
    img_smooth = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    smooth_image = Image.fromarray(img_smooth)
    
    # Step 2: Enhance colors dramatically
    color_enhancer = ImageEnhance.Color(smooth_image)
    candy_img = color_enhancer.enhance(2.0)  # Boost saturation
    
    # Step 3: Increase contrast for pop art effect
    contrast_enhancer = ImageEnhance.Contrast(candy_img)
    candy_img = contrast_enhancer.enhance(1.5)
    
    # Step 4: Slight brightness boost
    brightness_enhancer = ImageEnhance.Brightness(candy_img)
    candy_img = brightness_enhancer.enhance(1.1)
    
    # Step 5: Posterize for fewer color levels (candy-like effect)
    candy_img = ImageOps.posterize(candy_img, bits=4)
    
    # Step 6: Add a slight blur for dreamy effect
    candy_img = candy_img.filter(ImageFilter.GaussianBlur(radius=1))
    
    return candy_img

def get_cartoonization_styles():
    """
    Return available cartoonization styles (original 6 styles only)
    """
    return {
        "pencil_sketch": "Pencil Sketch",
        "colored_sketch": "Colored Sketch", 
        "classic_cartoon": "Vintage Style",
        "candy_style": "Candy Pop Art",
        "oil_painting": "Oil Painting",
        "pixel_art_style": "Pixel Art Style"
    }

def apply_cartoonization(image_path, style):
    """
    Apply the specified cartoonization style to the image (original 6 styles only)
    """
    try:
        print(f"DEBUG CARTOONIZATION: Applying style '{style}' to {image_path}")
        
        if style == "pencil_sketch":
            print("DEBUG: Executing pencil_sketch function")
            return pencil_sketch(image_path)
        elif style == "oil_painting":
            print("DEBUG: Executing oil_painting function")
            return oil_painting(image_path)
        elif style == "colored_sketch":
            print("DEBUG: Executing colored_sketch function")
            return colored_sketch(image_path)
        elif style == "classic_cartoon":
            print("DEBUG: Executing classic_cartoon function (AI Enhanced)")
            return classic_cartoon(image_path)
        elif style == "pixel_art_style":
            print("DEBUG: Executing pixel_art_style function")
            return pixel_art_style(image_path)
        elif style == "candy_style":
            print("DEBUG: Executing candy_style function")
            return candy_style(image_path)
        else:
            # Default to classic cartoon for unknown styles
            print(f"DEBUG: Unknown style '{style}', defaulting to classic cartoon")
            return classic_cartoon(image_path)
    except Exception as e:
        print(f"Error applying cartoonization: {e}")
        # Return original image on error
        return Image.open(image_path)