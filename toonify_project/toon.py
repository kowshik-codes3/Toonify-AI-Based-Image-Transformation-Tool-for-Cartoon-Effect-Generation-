<<<<<<< HEAD
import cv2
import streamlit as st
import numpy as np
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import os
from torchvision import transforms
import torchvision as tv
import torch.nn.functional as F
import re
import json

def download_file(outputing,style):
    buf = BytesIO()
    
    # convert to PIL image if it's a NumPy array
    if isinstance(outputing, np.ndarray):
        outputing.save(buf, format="PNG")
    elif isinstance(outputing, Image.Image):
        outputing.save(buf, format="PNG")
    else:
        raise TypeError("outputing must be a PIL Image or a NumPy array")
    
    buf.seek(0)
    st.download_button(
        label=" Download Cartoon",
        data=buf.getvalue(),
        file_name="cartoon_{style}.png".format(style=style),
        mime="image/png"
    )

def show_toonify(original_img, toonified_img, image_desc):
    
    st.session_state["cartoon_img"] = toonified_img  # store it
    # show both
    col1, col2 = st.columns(2)
    with col1:
        st.image(original_img, "Original")
    with col2:
        st.image(st.session_state["cartoon_img"], image_desc)
    
    download_file(st.session_state["cartoon_img"], image_desc)

def pencilSketch(input):
    # Load image
    img = cv2.imread(input)
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
    
    show_toonify(input, sketch, "pencil sketch")

def oilPainting(input):
    
    img = Image.open(input).convert("RGB")
    
    # Step 1: Smooth details, simulate brush blending
    smooth = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Step 2: create soft brushstroke texture
    gray = ImageOps.grayscale(smooth)
    blur = gray.filter(ImageFilter.FIND_EDGES)
    
    edges_blur = edges.filter(ImageFilter.GaussianBlur(radius=2.5))  # less blur
    
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
    
    # Display or return
    show_toonify(input, oil_paint, "Oil Painting")

def coloreuSketch(input):
    
    # load image
    img = cv2.imread(input)
    if img is None:
        raise ValueError("Error: Image not found or path is incorrect.")
    img = cv2.resize(img,(800,int(img.shape[0]*800/img.shape[1])))
    
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
    
    show_toonify(input, colored_sketch, "Colored Sketch")

def classic_cartoon(input):
    # load
    img = cv2.imread(input)
    if img is None:
        raise ValueError("Image not found")
    
    img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    line = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
    color = cv2.bilateralFilter(img, 11, 200, 200)
    cartoon = cv2.bitwise_and(color, color, mask=edges)
    
    show_toonify(input, cartoon, "Classic Cartoon")

class ConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride):
        super().__init__()
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)
    
    def forward(self, x):
        out = self.reflection_pad(x)
        out = self.conv2d(out)
        return out

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = ConvLayer(channels, channels, 3, 1)
        self.in1 = nn.InstanceNorm2d(channels, affine=True)
        self.conv2 = ConvLayer(channels, channels, 3, 1)
        self.in2 = nn.InstanceNorm2d(channels, affine=True)
    
    def forward(self, x):
        residual = x
        out = F.relu(self.in1(self.conv1(x)))
        out = self.in2(self.conv2(out))
        return out + residual

class UpsampleConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, upsample=None):
        super().__init__()
        self.upsample = upsample
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)
    
    def forward(self, x):
        if self.upsample:
            x = F.interpolate(x, scale_factor=self.upsample)
        out = self.reflection_pad(x)
        out = self.conv2d(out)
        return out

class TransformerNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = ConvLayer(3, 32, 9, 1)
        self.in1 = nn.InstanceNorm2d(32, affine=True)
        self.conv2 = ConvLayer(32, 64, 3, 2)
        self.in2 = nn.InstanceNorm2d(64, affine=True)
        self.conv3 = ConvLayer(64, 128, 3, 2)
        self.in3 = nn.InstanceNorm2d(128, affine=True)
        self.res1 = ResidualBlock(128)
        self.res2 = ResidualBlock(128)
        self.res3 = ResidualBlock(128)
        self.res4 = ResidualBlock(128)
        self.res5 = ResidualBlock(128)
        self.deconv1 = UpsampleConvLayer(128, 64, 3, 1, upsample=2)
        self.in4 = nn.InstanceNorm2d(64, affine=True)
        self.deconv2 = UpsampleConvLayer(64, 32, 3, 1, upsample=2)
        self.in5 = nn.InstanceNorm2d(32, affine=True)
        self.deconv3 = ConvLayer(32, 3, 9, 1)
    
    def forward(self, x):
        y = F.relu(self.in1(self.conv1(x)))
        y = F.relu(self.in2(self.conv2(y)))
        y = F.relu(self.in3(self.conv3(y)))
        y = self.res1(y)
        y = self.res2(y)
        y = self.res3(y)
        y = self.res4(y)
        y = self.res5(y)
        y = F.relu(self.in4(self.deconv1(y)))
        y = F.relu(self.in5(self.deconv2(y)))
        y = self.deconv3(y)
        return y


def cartoon_neural_style(input_input, style_model_path: str, res1ze: int = 512, add_edges: bool = True):
    
    device = torch.device("cpu")
    
    # load image
    if isinstance(image_input, str):
        if image_input.startswith("http://") or image_input.startswith("https://"):
            import requests
            response = requests.get(image_input)
            input_image = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            input_image = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        input_image = image_input.convert("RGB")
    else:
        raise ValueError("image_input must be URL, local path, or PIL Image")
    
    # load model
    model = TransformerNet()
    state_dict = torch.load(style_model_path, map_location=device)
    # remove 'module.' prefix from state keys
    for k in list(state_dict.keys()):
        if re.search("^module\.running_(mean|var)", k):
            del state_dict[k]
    model.load_state_dict(state_dict, strict=False)
=======
import cv2
import streamlit as st
import numpy as np
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import os
from torchvision import transforms
import torchvision as tv
import torch.nn.functional as F
import re
import json

def download_file(outputing,style):
    buf = BytesIO()
    
    # convert to PIL image if it's a NumPy array
    if isinstance(outputing, np.ndarray):
        outputing.save(buf, format="PNG")
    elif isinstance(outputing, Image.Image):
        outputing.save(buf, format="PNG")
    else:
        raise TypeError("outputing must be a PIL Image or a NumPy array")
    
    buf.seek(0)
    st.download_button(
        label=" Download Cartoon",
        data=buf.getvalue(),
        file_name="cartoon_{style}.png".format(style=style),
        mime="image/png"
    )

def show_toonify(original_img, toonified_img, image_desc):
    
    st.session_state["cartoon_img"] = toonified_img  # store it
    # show both
    col1, col2 = st.columns(2)
    with col1:
        st.image(original_img, "Original")
    with col2:
        st.image(st.session_state["cartoon_img"], image_desc)
    
    download_file(st.session_state["cartoon_img"], image_desc)

def pencilSketch(input):
    # Load image
    img = cv2.imread(input)
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
    
    show_toonify(input, sketch, "pencil sketch")

def oilPainting(input):
    
    img = Image.open(input).convert("RGB")
    
    # Step 1: Smooth details, simulate brush blending
    smooth = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Step 2: create soft brushstroke texture
    gray = ImageOps.grayscale(smooth)
    blur = gray.filter(ImageFilter.FIND_EDGES)
    
    edges_blur = edges.filter(ImageFilter.GaussianBlur(radius=2.5))  # less blur
    
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
    
    # Display or return
    show_toonify(input, oil_paint, "Oil Painting")

def coloreuSketch(input):
    
    # load image
    img = cv2.imread(input)
    if img is None:
        raise ValueError("Error: Image not found or path is incorrect.")
    img = cv2.resize(img,(800,int(img.shape[0]*800/img.shape[1])))
    
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
    
    show_toonify(input, colored_sketch, "Colored Sketch")

def classic_cartoon(input):
    # load
    img = cv2.imread(input)
    if img is None:
        raise ValueError("Image not found")
    
    img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    line = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
    color = cv2.bilateralFilter(img, 11, 200, 200)
    cartoon = cv2.bitwise_and(color, color, mask=edges)
    
    show_toonify(input, cartoon, "Classic Cartoon")

class ConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride):
        super().__init__()
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)
    
    def forward(self, x):
        out = self.reflection_pad(x)
        out = self.conv2d(out)
        return out

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = ConvLayer(channels, channels, 3, 1)
        self.in1 = nn.InstanceNorm2d(channels, affine=True)
        self.conv2 = ConvLayer(channels, channels, 3, 1)
        self.in2 = nn.InstanceNorm2d(channels, affine=True)
    
    def forward(self, x):
        residual = x
        out = F.relu(self.in1(self.conv1(x)))
        out = self.in2(self.conv2(out))
        return out + residual

class UpsampleConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, upsample=None):
        super().__init__()
        self.upsample = upsample
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)
    
    def forward(self, x):
        if self.upsample:
            x = F.interpolate(x, scale_factor=self.upsample)
        out = self.reflection_pad(x)
        out = self.conv2d(out)
        return out

class TransformerNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = ConvLayer(3, 32, 9, 1)
        self.in1 = nn.InstanceNorm2d(32, affine=True)
        self.conv2 = ConvLayer(32, 64, 3, 2)
        self.in2 = nn.InstanceNorm2d(64, affine=True)
        self.conv3 = ConvLayer(64, 128, 3, 2)
        self.in3 = nn.InstanceNorm2d(128, affine=True)
        self.res1 = ResidualBlock(128)
        self.res2 = ResidualBlock(128)
        self.res3 = ResidualBlock(128)
        self.res4 = ResidualBlock(128)
        self.res5 = ResidualBlock(128)
        self.deconv1 = UpsampleConvLayer(128, 64, 3, 1, upsample=2)
        self.in4 = nn.InstanceNorm2d(64, affine=True)
        self.deconv2 = UpsampleConvLayer(64, 32, 3, 1, upsample=2)
        self.in5 = nn.InstanceNorm2d(32, affine=True)
        self.deconv3 = ConvLayer(32, 3, 9, 1)
    
    def forward(self, x):
        y = F.relu(self.in1(self.conv1(x)))
        y = F.relu(self.in2(self.conv2(y)))
        y = F.relu(self.in3(self.conv3(y)))
        y = self.res1(y)
        y = self.res2(y)
        y = self.res3(y)
        y = self.res4(y)
        y = self.res5(y)
        y = F.relu(self.in4(self.deconv1(y)))
        y = F.relu(self.in5(self.deconv2(y)))
        y = self.deconv3(y)
        return y


def cartoon_neural_style(input_input, style_model_path: str, res1ze: int = 512, add_edges: bool = True):
    
    device = torch.device("cpu")
    
    # load image
    if isinstance(image_input, str):
        if image_input.startswith("http://") or image_input.startswith("https://"):
            import requests
            response = requests.get(image_input)
            input_image = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            input_image = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        input_image = image_input.convert("RGB")
    else:
        raise ValueError("image_input must be URL, local path, or PIL Image")
    
    # load model
    model = TransformerNet()
    state_dict = torch.load(style_model_path, map_location=device)
    # remove 'module.' prefix from state keys
    for k in list(state_dict.keys()):
        if re.search("^module\.running_(mean|var)", k):
            del state_dict[k]
    model.load_state_dict(state_dict, strict=False)
>>>>>>> b9aeece1db44d5c9240ec23dcfbd048d90b6ab50
    model.to(device).eval()