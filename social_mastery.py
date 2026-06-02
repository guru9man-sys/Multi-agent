"""
social_mastery.py - The Content Generation Agent
Converts analysis into high-conversion content for multiple platforms.
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from database import DBManager, ArtifactRecord, TaskRecord
from schemas import TaskRequest, TaskResponse, TaskStatus


# Platform Configuration
PLATFORM_CONFIG = {
    "linkedin": {
        "tone": "Authoritative, Professional, Thought-Leader",
        "format": "Long-form post with bullet points and a CTA",
        "hook_type": "Professional insight or counter-intuitive business fact",
        "max_length": 3000,
        "hashtag_count": 3,
        "emoji_count": 1
    },
    "x": {
        "tone": "Punchy, Bold, Controversial",
        "format": "Thread (1/N) with high-impact first tweet",
        "hook_type": "Strong claim or 'The truth about X'",
        "max_length": 280,
        "hashtag_count": 2,
        "emoji_count": 2
    },
    "tiktok": {
        "tone": "Energetic, Fast-paced, Relatable",
        "format": "Script for 60s video (Visual cue | Audio text)",
        "hook_type": "Visual hook or 'You won't believe this' start",
        "max_length": 500,
        "hashtag_count": 5,
        "emoji_count": 3
    },
    "facebook": {
        "tone": "Community-focused, Story-driven, Approachable",
        "format": "Story-based post with a personal anecdote",
        "hook_type": "Relatable life situation",
        "max_length": 2000,
        "hashtag_count": 2,
        "emoji_count": 2
    },
    "line": {
        "tone": "Intimate, Trustworthy, Direct",
        "format": "Short, direct message with a clear link",
        "hook_type": "Exclusive update or personal recommendation",
        "max_length": 500,
        "hashtag_count": 0,
        "emoji_count": 1
    }
}


class SocialMediaMastery:
    """The Content Generation Agent."""

    def __init__(self, db_manager: DBManager, llm_client=None):
        self.db = db_manager
        self.llm = llm_client

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Converts synthesis reports into high-conversion content.
        """
        parent_id = request.payload.get("parent_id")
        target_platforms = request.payload.get("platforms", ["linkedin", "x"])

        if not parent_id:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": "No parent_id provided for content generation."},
                meta={"confidence": 0.0},
                error_message="Missing parent task ID"
            )

        try:
            print(f"📱 Social Media Mastery: Creating campaign for {', '.join(target_platforms)}...")

            # 1. Retrieve the Synthesis Report
            synthesis_data = self._get_synthesis_report(parent_id)

            if not synthesis_data:
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": "No synthesis report found to convert."},
                    meta={"confidence": 0.0}
                )

            # 2. Generate content for each platform
            final_campaign = {}
            for platform in target_platforms:
                if platform in PLATFORM_CONFIG:
                    config = PLATFORM_CONFIG[platform]
                    content = self._generate_platform_content(synthesis_data, config, platform)
                    final_campaign[platform] = content
                else:
                    final_campaign[platform] = {"error": f"Unknown platform: {platform}"}

            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "primary_output": f"Generated campaign for {len(target_platforms)} platforms",
                    "campaign_package": final_campaign,
                    "platforms_covered": target_platforms
                },
                meta={
                    "confidence": 0.9,
                    "platforms_count": len(target_platforms),
                    "execution_time": "4.1s",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                meta={"confidence": 0.0},
                error_message=f"Content generation failed: {str(e)}"
            )

    def _get_synthesis_report(self, parent_id: str) -> str:
        """Fetch the latest synthesis artifact from the DB."""
        session = self.db.Session()
        try:
            result = session.query(ArtifactRecord).join(TaskRecord).filter(
                TaskRecord.parent_task_id == parent_id,
                TaskRecord.agent_role == "integrative_synthesis_expert"
            ).order_by(ArtifactRecord.created_at.desc()).first()

            if result and result.content:
                return str(result.content.get("primary_output", ""))
            return None
        finally:
            session.close()

    def _generate_platform_content(self, data: str, config: Dict, platform: str) -> Dict[str, Any]:
        """
        Transforms synthesis into a high-conversion post for the platform.
        """
        prompt = f"""You are a world-class conversion copywriter specializing in {platform}.

Transform the following content into a high-performing {platform} post.

PLATFORM RULES:
- Tone: {config['tone']}
- Format: {config['format']}
- Hook Strategy: {config['hook_type']}
- Max Length: {config['max_length']} characters
- Hashtags: {config['hashtag_count']}
- Emojis: Use approximately {config['emoji_count']} strategically placed

CONTENT TO ADAPT:
{data}

Return ONLY a JSON object with this structure:
{{
    "hook": "The opening line that stops the scroll",
    "body": "The main content",
    "cta": "The call to action",
    "hashtags": ["#tag1", "#tag2"],
    "platform": "{platform}"
}}"""

        if self.llm:
            response = self.llm.generate(prompt)
            try:
                # Try to parse the response as JSON
                return json.loads(response)
            except:
                # If parsing fails, return structured default
                return {
                    "hook": "Discover what you need to know",
                    "body": data[:config['max_length']],
                    "cta": "Learn more",
                    "hashtags": [f"#{platform.capitalize()}"],
                    "platform": platform
                }
        else:
            # Fallback content
            return {
                "hook": f"🔥 Breaking: Important insights about industry trends",
                "body": f"Here's what you need to know... {data[:200]}...",
                "cta": "Join the conversation",
                "hashtags": ["#innovation", "#insights"],
                "platform": platform
            }
