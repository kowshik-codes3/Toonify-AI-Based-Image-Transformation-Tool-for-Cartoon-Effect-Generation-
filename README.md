<<<<<<< HEAD
# Toonify
=======
# 🎨 Toonify - Image Cartoonization App

A Flask-based web application for transforming images into various cartoon styles.

## 🌟 Features

### 6 Cartoon Styles Available:
1. **Pencil Sketch** - Simple edge detection sketch
2. **Colored Sketch** - Artistic colored sketch  
3. **Classic Cartoon** ⭐ - AI-enhanced with Stable Diffusion (optional)
4. **Oil Painting** - Painterly texture effect
5. **Pixel Art Style** - Retro pixelated transformation
6. **Candy Pop Art** - Vibrant pop art colors

### Core Features:
- 🖼️ Image upload and processing
- 💳 Payment integration (Razorpay)
- 👤 User authentication and profiles
- 📊 Dynamic pricing system
- 📱 Responsive web interface

## 🚀 Quick Start

### Installation

1. **Basic Installation** (OpenCV styles only):
```bash
pip install -r requirements.txt
```

2. **With AI Enhancement** (for Classic Cartoon):
   - Edit `requirements.txt` and uncomment the AI libraries section
   - Run: `pip install torch diffusers transformers`

### Run the Application
```bash
python app.py
```

## 📁 Project Structure

```
toonify_project/
├── app.py              # Main Flask application
├── cartoonization.py   # Image processing functions
├── auth.py            # User authentication
├── database.py        # Database operations
├── dynamic_pricing.py # Pricing configuration
├── templates/         # HTML templates
├── static/           # CSS, JS, images
└── uploads/          # Processed images
```

## 🎨 Technical Details

- **5 styles** use fast OpenCV implementations
- **1 style** (Classic Cartoon) optionally uses AI for enhanced quality
- Fallback system: AI styles revert to OpenCV if model unavailable
- Built with Flask, OpenCV, PIL, and optional PyTorch/Stable Diffusion

## 💡 Performance

- **Fast**: 5/6 styles use lightweight OpenCV (< 1 second processing)
- **Quality**: AI enhancement available for premium results
- **Reliable**: Fallback system ensures app always works

---

*Clean, efficient, and user-friendly cartoon generation! 🎉*
>>>>>>> 00f04eb2f (Initial clean commit - Complete Toonify application)
