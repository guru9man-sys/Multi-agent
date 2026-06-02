"""
visual_design_agent.py - Visual Design Agent
Specializes in image generation, text overlay, and graphic layout design.
"""

import os
import uuid
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from database import DBManager
from schemas import TaskRequest, TaskResponse, TaskStatus
from utils.logger import logger
from config import config

class VisualDesignAgent:
    """Agent responsible for creating and editing visual content."""

    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.output_dir = "outputs/visuals"
        os.makedirs(self.output_dir, exist_ok=True)

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Main execution loop for visual design tasks.
        """
        logger.info(f"VisualDesignAgent executing | TaskID: {request.task_id} | Action: {request.action}")
        
        try:
            if request.action == "generate":
                return self._generate_image(request)
            elif request.action == "overlay_text":
                return self._overlay_text(request)
            elif request.action == "design_layout":
                return self._design_layout(request)
            else:
                return self._handle_unknown_action(request)
        except Exception as e:
            logger.error(f"VisualDesignAgent Error | TaskID: {request.task_id} | Error: {str(e)}")
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message=f"Visual design failed: {str(e)}"
            )

    def _generate_image(self, request: TaskRequest) -> TaskResponse:
        """
        Generates an image using an external API (e.g., DALL-E 3).
        """
        prompt = request.payload.get("prompt", "A professional high-quality design")
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        
        # Mocking API call for demonstration - In production, use openai.Image.create()
        image_id = str(uuid.uuid4())
        file_path = os.path.join(self.output_dir, f"{image_id}.png")
        
        # Create a placeholder image to simulate API output
        img = Image.new('RGB', (1024, 1024), color=(73, 109, 137))
        img.save(file_path)
        
        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.COMPLETED,
            artifacts={
                "image_url": file_path,
                "image_id": image_id,
                "prompt_used": prompt
            },
            meta={"engine": "DALL-E-3-Mock", "resolution": "1024x1024"}
        )

    def _overlay_text(self, request: TaskRequest) -> TaskResponse:
        """
        Adds text overlays to an existing image.
        """
        image_path = request.payload.get("image_path")
        text = request.payload.get("text", "Default Text")
        position = request.payload.get("position", (50, 50))
        font_size = request.payload.get("font_size", 40)
        color = request.payload.get("color", "white")

        if not image_path or not os.path.exists(image_path):
            raise ValueError(f"Source image not found at {image_path}")

        logger.info(f"Overlaying text: '{text[:20]}...' on {image_path}")
        
        with Image.open(image_path) as img:
            draw = ImageDraw.Draw(img)
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            draw.text(position, text, font=font, fill=color)
            
            output_id = str(uuid.uuid4())
            output_path = os.path.join(self.output_dir, f"overlay_{output_id}.png")
            img.save(output_path)

        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.COMPLETED,
            artifacts={"image_url": output_path},
            meta={"action": "text_overlay"}
        )

    def _design_layout(self, request: TaskRequest) -> TaskResponse:
        """
        Creates a structured layout (e.g., a social media banner).
        """
        platform = request.payload.get("platform", "instagram")
        content = request.payload.get("content", {})
        
        # Define dimensions based on platform
        dims = {"instagram": (1080, 1080), "linkedin": (1200, 627), "youtube": (1280, 720)}
        size = dims.get(platform, (1080, 1080))
        
        logger.info(f"Designing {platform} layout with size {size}")
        
        img = Image.new('RGB', size, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Simple layout: Header and Body
        try:
            font_h = ImageFont.truetype("arial.ttf", 60)
            font_b = ImageFont.truetype("arial.ttf", 30)
        except:
            font_h = font_b = ImageFont.load_default()

        draw.text((50, 50), content.get("title", "Title"), font=font_h, fill="black")
        draw.text((50, 150), content.get("body", "Body content..."), font=font_b, fill="gray")
        
        output_id = str(uuid.uuid4())
        output_path = os.path.join(self.output_dir, f"layout_{output_id}.png")
        img.save(output_path)

        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.COMPLETED,
            artifacts={"image_url": output_path},
            meta={"platform": platform, "dimensions": size}
        )

    def _handle_unknown_action(self, request: TaskRequest) -> TaskResponse:
        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.FAILED,
            artifacts={"error": f"Action {request.action} not supported by VisualDesignAgent"},
            error_message="Unsupported visual action"
        )
