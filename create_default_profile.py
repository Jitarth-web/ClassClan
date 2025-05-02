from PIL import Image, ImageDraw, ImageFont
import os

# Create a new image with a white background
size = (200, 200)
img = Image.new('RGB', size, color='#2C3E50')

# Get a drawing context
draw = ImageDraw.Draw(img)

# Draw a circle in the center
circle_center = (100, 100)
circle_radius = 60
circle_color = '#ECF0F1'
draw.ellipse([circle_center[0] - circle_radius,
              circle_center[1] - circle_radius,
              circle_center[0] + circle_radius,
              circle_center[1] + circle_radius],
             fill=circle_color)

# Draw a smaller circle for the head
head_radius = 25
head_center = (100, 85)
draw.ellipse([head_center[0] - head_radius,
              head_center[1] - head_radius,
              head_center[0] + head_radius,
              head_center[1] + head_radius],
             fill='#2C3E50')

# Draw a larger circle for the body
body_radius = 40
body_center = (100, 160)
draw.ellipse([body_center[0] - body_radius,
              body_center[1] - body_radius,
              body_center[0] + body_radius,
              body_center[1] - body_radius/2],
             fill='#2C3E50')

# Save the image
output_path = os.path.join('static', 'uploads', 'default_profile.png')
img.save(output_path, 'PNG')
print(f"Default profile image created at: {output_path}")
