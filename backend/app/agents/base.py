import logging
from typing import Any, Dict, Optional, Type
import json
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger("saarthi.agents")

class BaseAgent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.client = None
        self.openai_client = None
        self.use_real_ai = False
        
        # Initialize Google GenAI client if key is available
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.use_real_ai = True
                logger.info(f"Agent {self.name} initialized with Google Gemini API.")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")
                
        # Initialize OpenAI client if key is available and Gemini is not
        elif settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.use_real_ai = True
                logger.info(f"Agent {self.name} initialized with OpenAI API.")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI Client: {e}")
        
        if not self.use_real_ai:
            logger.info(f"Agent {self.name} initialized in MOCK Mode.")

    def run_llm(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        response_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        """Runs the LLM completion with schemas if supported, otherwise returns plain text."""
        if not self.use_real_ai:
            raise ValueError("LLM client not configured. Use local mock methods.")

        # Real Gemini Call
        if self.client:
            from google.genai import types
            try:
                config_args = {}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema
                
                config = types.GenerateContentConfig(**config_args)
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API call failed for agent {self.name}: {e}")
                # Fallback to OpenAI if configured, else raise
                if not settings.OPENAI_API_KEY:
                    raise e
                    
        # Real OpenAI Call
        if self.openai_client:
            try:
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                kwargs = {}
                if response_schema:
                    kwargs["response_format"] = {"type": "json_object"}
                    # Append reminder to prompt to format as json fitting the schema
                    prompt += f"\nReturn a JSON object that conforms to this schema: {json.dumps(response_schema.model_json_schema())}"
                    messages[-1]["content"] = prompt

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI API call failed for agent {self.name}: {e}")
                raise e

        raise ValueError("No live AI API clients available.")
        
    def mock_response(self, fallback_data: Any) -> Any:
        """Returns the mock fallback data directly."""
        return fallback_data
