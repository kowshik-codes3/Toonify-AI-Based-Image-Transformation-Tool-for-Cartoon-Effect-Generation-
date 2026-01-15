#!/usr/bin/env python3
"""
Dynamic pricing configuration for different cartoon styles
"""

def get_style_pricing():
    """
    Return pricing for different cartoon styles in INR
    """
    return {
        # Basic styles - lower price
        "pencil_sketch": {
            "price_inr": 30,
            "display_name": "Pencil Sketch",
            "description": "Simple pencil sketch effect",
            "tier": "basic"
        },
        "colored_sketch": {
            "price_inr": 40, 
            "display_name": "Colored Sketch",
            "description": "Artistic colored sketch",
            "tier": "standard"
        },
        
        # Standard styles - medium price
        "classic_cartoon": {
            "price_inr": 50,
            "display_name": "Vintage Style", 
            "description": "Vintage grayscale photo effect",
            "tier": "standard"
        },
        "candy_style": {
            "price_inr": 55,
            "display_name": "Candy Pop Art",
            "description": "Vibrant pop art style", 
            "tier": "standard"
        },
        
        # Premium styles - higher price
        "oil_painting": {
            "price_inr": 75,
            "display_name": "Oil Painting",
            "description": "Realistic oil painting effect",
            "tier": "premium"
        },
        "pixel_art_style": {
            "price_inr": 60,
            "display_name": "Pixel Art Style", 
            "description": "Retro pixel art transformation",
            "tier": "premium"
        }
    }

def get_price_for_style(style_key):
    """
    Get price for a specific style
    """
    pricing = get_style_pricing()
    return pricing.get(style_key, {}).get('price_inr', 50)  # Default to 50 if style not found

def get_style_display_info(style_key):
    """
    Get complete display information for a style including price
    """
    pricing = get_style_pricing()
    return pricing.get(style_key, {
        "price_inr": 50,
        "display_name": style_key.replace('_', ' ').title(),
        "description": "Cartoon transformation",
        "tier": "standard"
    })

def get_all_styles_with_pricing():
    """
    Get all available styles with their pricing information
    """
    return get_style_pricing()

if __name__ == '__main__':
    # Test the pricing system
    pricing = get_style_pricing()
    print("🎨 Cartoon Style Pricing:")
    print("=" * 50)
    
    for style_key, info in pricing.items():
        print(f"🎭 {info['display_name']:<18} - ₹{info['price_inr']:<3} ({info['tier']})")
        print(f"   {info['description']}")
        print()
    
    print("=" * 50)
    print(f"📊 Price Range: ₹{min(p['price_inr'] for p in pricing.values())} - ₹{max(p['price_inr'] for p in pricing.values())}")