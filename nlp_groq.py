"""
nlp_groq.py - Free natural language to Boolean using Groq
"""

from groq import Groq
import os

class GroqNLParser:
    """Convert natural language to Boolean expressions using Groq API"""
    
    def __init__(self, api_key=None):
        """Initialize with Groq API key"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required.")
        
        self.client = Groq(api_key=self.api_key)
        # llama-3.1-8b-instant is fast (560 tokens/sec), has 131K context, and is free
        self.model = "llama-3.1-8b-instant"
    
    def parse(self, user_request):
        """Convert natural language to Boolean expression"""
        
        prompt = f"""Convert this genetic circuit description to a Boolean expression.
        
Rules:
- Variables: IPTG, aTc, Arabinose only
- AND: use '.'
- OR: use '+'
- NOT: use "'" after the variable (example: IPTG' means NOT IPTG)
- Return ONLY the expression, no explanation, no extra text

Examples:
"IPTG and aTc" → IPTG.aTc
"IPTG but not aTc" → IPTG.aTc'
"turn on when IPTG is present AND aTc is absent" → IPTG.aTc'
"either aTc or Arabinose" → aTc+Arabinose
"IPTG present, aTc absent, and Arabinose present" → IPTG.aTc'.Arabinose

Description: {user_request}

Boolean expression:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a synthetic biology assistant. Convert descriptions to Boolean expressions. Return only the expression, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            expression = response.choices[0].message.content.strip()

             # Only remove SMART quotes, NOT the NOT operator
            expression = expression.replace('’', "'")  # Replace fancy right quote with straight quote
            expression = expression.replace('‘', "'")  # Replace fancy left quote with straight quote
            expression = expression.replace('"', '')   # Remove double quotes
            expression = expression.replace('`', "'")  # Replace backtick with straight quote

            # Clean up any extra quotes
            # expression = expression.replace('"', '').replace("'", '').strip()
            return expression
        except Exception as e:
            print(f"Groq error: {e}")
            return None