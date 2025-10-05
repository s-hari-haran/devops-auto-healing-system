import os
import sys
import json
from anthropic import Anthropic

# The newest Anthropic model is "claude-sonnet-4-20250514", not "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022" nor "claude-3-sonnet-20240229".
DEFAULT_MODEL_STR = "claude-sonnet-4-20250514"

class ClaudeClient:
    def __init__(self):
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if not anthropic_key:
            sys.exit('ANTHROPIC_API_KEY environment variable must be set')
        
        self.client = Anthropic(api_key=anthropic_key)
        self.model = DEFAULT_MODEL_STR
    
    def analyze_error(self, error_log, related_code, file_path=""):
        """Analyze error log and suggest fix using Claude API"""
        
        prompt = f'''You are a DevOps assistant. Analyze the following error log and the related source code.

### ERROR LOG:
{error_log}

### SOURCE CODE (from {file_path}):
{related_code}

Return a short explanation of the issue, and a suggested code fix with an explanation.

Respond in JSON format:
{{
  "explanation": "Brief explanation of what caused the error",
  "suggested_fix": "Description of how to fix it",
  "fixed_code": "The complete corrected code"
}}'''

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Extract text from response blocks
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text = block.text
                    break
            
            if not response_text:
                return {
                    "explanation": "No text response from Claude",
                    "suggested_fix": "Unable to get response from AI",
                    "fixed_code": related_code
                }
            
            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # If Claude doesn't return pure JSON, extract it
                if '{' in response_text and '}' in response_text:
                    start = response_text.index('{')
                    end = response_text.rindex('}') + 1
                    result = json.loads(response_text[start:end])
                    return result
                else:
                    return {
                        "explanation": "Could not parse Claude response",
                        "suggested_fix": response_text,
                        "fixed_code": related_code
                    }
                    
        except Exception as e:
            return {
                "explanation": f"Error calling Claude API: {str(e)}",
                "suggested_fix": "Please check your API key and try again",
                "fixed_code": related_code
            }
