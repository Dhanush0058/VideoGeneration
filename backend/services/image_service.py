import os
import io
import random
import httpx
from PIL import Image, ImageDraw, ImageFont
from backend.config import settings

class ImageService:
    def __init__(self):
        self.provider = settings.IMAGE_PROVIDER.upper()
        self.model_name = settings.IMAGE_MODEL
        self.hf_token = settings.HF_TOKEN

    async def generate_image(
        self, 
        prompt: str, 
        output_path: str, 
        title: str = "", 
        on_screen_text: list = None
    ) -> str:
        """
        Generates or draws a visual for the scene and saves it to output_path.
        Returns the path to the saved image.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        on_screen_text = on_screen_text or []

        # Try Pollinations first if selected (fully keyless, free, very high availability)
        if self.provider == "POLLINATIONS":
            try:
                await self._generate_pollinations(prompt, output_path)
                return output_path
            except Exception as e:
                print(f"Pollinations Image API failed: {e}. Falling back to programmatic diagram engine.")

        # If provider is HF_API and token is present, try remote generation
        elif self.provider == "HF_API" and self.hf_token:
            try:
                await self._generate_hf_api(prompt, output_path)
                return output_path
            except Exception as e:
                print(f"HF Image API failed: {e}. Falling back to programmatic diagram engine.")
        
        # Fallback diagram drawing
        self._generate_diagram(title, on_screen_text, prompt, output_path)
        return output_path

    async def _generate_pollinations(self, prompt: str, output_path: str):
        """Generates image via Pollinations.ai (free, keyless, high availability)."""
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true&seed={random.randint(1, 1000000)}"
        
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.get(url)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(res.content)
            else:
                raise ValueError(f"Pollinations returned status code {res.status_code}")

    async def _generate_hf_api(self, prompt: str, output_path: str):
        """Generates image via Hugging Face Serverless Inference API."""
        url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": prompt}
        
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(res.content)
            else:
                raise ValueError(f"HF API returned status code {res.status_code}: {res.text}")

    def _generate_diagram(self, title: str, on_screen_text: list, prompt: str, output_path: str):
        """
        Generates a premium, modern, educational diagram/slide using Pillow.
        Draws boxes, arrows, gradients, and text overlays in 16:9 format.
        """
        # Canvas dimensions: 1080p Full HD (1920 x 1080)
        width, height = 1920, 1080
        
        # Select a modern educational color theme based on the title length or hash
        themes = [
            {"bg_start": (15, 23, 42), "bg_end": (30, 41, 59), "accent": (56, 189, 248), "text": (248, 250, 252)},  # Slate/Blue (Default Tech)
            {"bg_start": (9, 9, 11), "bg_end": (39, 39, 42), "accent": (168, 85, 247), "text": (250, 250, 250)},   # Charcoal/Purple (Modern AI)
            {"bg_start": (2, 43, 58), "bg_end": (5, 80, 100), "accent": (45, 212, 191), "text": (240, 253, 250)},  # Teal/Petrole (Science)
            {"bg_start": (24, 24, 27), "bg_end": (63, 63, 70), "accent": (244, 63, 94), "text": (255, 241, 242)}   # Slate/Pink (Creative)
        ]
        
        # Consistent theme selection based on title hash
        theme_index = abs(hash(title)) % len(themes)
        theme = themes[theme_index]
        
        # Create base image
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        for y in range(height):
            # Interpolate background color
            r = int(theme["bg_start"][0] + (theme["bg_end"][0] - theme["bg_start"][0]) * (y / height))
            g = int(theme["bg_start"][1] + (theme["bg_end"][1] - theme["bg_start"][1]) * (y / height))
            b = int(theme["bg_start"][2] + (theme["bg_end"][2] - theme["bg_start"][2]) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
            
        # Draw a subtle background grid pattern
        grid_spacing = 80
        grid_color = (theme["bg_end"][0] + 5, theme["bg_end"][1] + 5, theme["bg_end"][2] + 5)
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Attempt to load fonts, fall back to default
        try:
            # Try to use standard windows fonts
            font_title = ImageFont.truetype("arial.ttf", 64)
            font_body = ImageFont.truetype("arial.ttf", 40)
            font_detail = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            # Fallback to default pillow fonts
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_detail = ImageFont.load_default()

        # Draw Title Header (top-left)
        draw.text((100, 100), title.upper(), fill=theme["accent"], font=font_title)
        draw.line([(100, 180), (400, 180)], fill=theme["accent"], width=6)
        
        # Draw visual prompt description as a subtle caption at the bottom
        caption_text = f"Visual representation: {prompt[:120]}..."
        draw.text((100, 980), caption_text, fill=(150, 150, 150), font=font_detail)

        # Layout diagrams based on on_screen_text count
        if len(on_screen_text) > 0:
            card_count = len(on_screen_text)
            
            # Calculate coordinates for horizontal flow cards
            card_width = 420
            card_height = 260
            gap = 100
            
            total_cards_width = (card_width * card_count) + (gap * (card_count - 1))
            start_x = (width - total_cards_width) // 2
            card_y = (height - card_height) // 2 + 50
            
            for i, text in enumerate(on_screen_text):
                cx = start_x + (i * (card_width + gap))
                
                # Card background (semi-transparent glassmorphism style)
                card_bg = (theme["bg_end"][0] + 15, theme["bg_end"][1] + 15, theme["bg_end"][2] + 20)
                draw.rounded_rectangle(
                    [(cx, card_y), (cx + card_width, card_y + card_height)],
                    radius=20,
                    fill=card_bg,
                    outline=theme["accent"] if i == 0 else (100, 100, 100),
                    width=3
                )
                
                # Card badge index
                badge_bg = theme["accent"] if i == 0 else (120, 120, 120)
                draw.rounded_rectangle(
                    [(cx + 30, card_y - 20), (cx + 100, card_y + 15)],
                    radius=10,
                    fill=badge_bg
                )
                draw.text((cx + 55, card_y - 12), f"0{i+1}", fill=(255, 255, 255), font=font_detail)

                # Text breaking for card body
                words = text.split()
                lines = []
                current_line = []
                for word in words:
                    if len(" ".join(current_line + [word])) * 12 > card_width - 60:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    lines.append(" ".join(current_line))
                
                # Draw lines inside the card
                text_y = card_y + 60
                for line in lines[:3]:
                    draw.text((cx + 40, text_y), line, fill=theme["text"], font=font_body)
                    text_y += 50
                
                # Draw connector arrow to next card
                if i < card_count - 1:
                    arrow_start_x = cx + card_width + 10
                    arrow_end_x = cx + card_width + gap - 10
                    arrow_y = card_y + (card_height // 2)
                    
                    # Draw arrow line
                    draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)], fill=theme["accent"], width=4)
                    # Draw arrowhead
                    draw.polygon([
                        (arrow_end_x, arrow_y),
                        (arrow_end_x - 15, arrow_y - 10),
                        (arrow_end_x - 15, arrow_y + 10)
                    ], fill=theme["accent"])
        else:
            # If no items, draw a central beautiful graphic representing study concepts
            cx, cy = width // 2, height // 2 + 50
            draw.circle((cx, cy), 180, fill=None, outline=theme["accent"], width=6)
            draw.circle((cx, cy), 120, fill=(theme["bg_end"][0]+10, theme["bg_end"][1]+10, theme["bg_end"][2]+15))
            
            draw.text((cx - 100, cy - 20), "STUDY FLOW", fill=theme["text"], font=font_body)
            draw.text((cx - 80, cy + 30), "AI ENGINE", fill=theme["accent"], font=font_detail)
            
            # Draw surrounding orbital nodes
            for angle in [0, 60, 120, 180, 240, 300]:
                import math
                rad = math.radians(angle)
                nx = cx + int(260 * math.cos(rad))
                ny = cy + int(260 * math.sin(rad))
                draw.circle((nx, ny), 25, fill=theme["accent"])
                draw.line([(cx, cy), (nx, ny)], fill=theme["accent"], width=2)
                
        # Save image
        img.save(output_path, "PNG")
