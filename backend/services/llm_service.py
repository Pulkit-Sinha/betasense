import re
import json
import os
import sys
from typing import Optional
from langchain_aws import ChatBedrock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import LLMModel


class LLMService:

    def __init__(self, model_kwargs: dict = None):
        # Always use Claude 4 Sonnet
        self.model = ChatBedrock(
            region_name='us-west-2',
            model_id=LLMModel.CLAUDE_4_SONNET.value,
            provider='anthropic',
            model_kwargs=model_kwargs
        )

        enable_llm = os.getenv("ENABLE_LLM_SERVICE", "true").lower() == "true"
        if not enable_llm:
            raise Exception("LLM Service is not enabled")
        print(f"INIT LLM : {LLMModel.CLAUDE_4_SONNET.value}")

    def is_safe_prompt(self, prompt: str) -> bool:
        restricted_keywords = [
            # Malicious software
            'hack', 'exploit', 'attack', 'virus', 'malware',
            'phishing', 'ransomware', 'trojan', 'worm', 'spyware',
            'backdoor', 'botnet', 'keylogger', 'rootkit', 'ddos',
            'crack', 'breach', 'infiltrate', 'compromise', 'hijack',

            # Network attacks
            'injection', 'overflow', 'mitm', 'sniffer', 'spoofing',
            'bruteforce', 'intercept', 'shell', 'exploit',
            'port scan', 'denial of service', 'zero day', 'vulnerability',

            # System manipulation
            'escalate', 'privilege', 'bypass', 'corrupt', 'terminate',
            'disable', 'override', 'encrypt', 'decrypt', 'forge',
            'sudo', 'root access', 'system files', 'registry',

            # Social engineering
            'steal', 'fraud', 'scam', 'impersonate', 'spam',
            'blackmail', 'extort', 'deceive', 'manipulate', 'bribe',
            'counterfeit', 'illegal', 'credential', 'identity theft',

            # Additional threats
            'malicious', 'exploit kit', 'reverse shell', 'rat',
            'crypto mining', 'command injection', 'buffer overflow',
            'sql injection', 'xss', 'csrf', 'remote code execution'
        ]

        dangerous_words = [word for word in restricted_keywords if word in prompt.lower().split(' ')]
        if dangerous_words:
            print(f"Dangerous words found: {dangerous_words}")
        return not any(word for word in restricted_keywords if word in prompt.lower().split(' '))

    def _get_messages(self, system_prompt: str, user_prompt: str) -> list:
        return [
            ("system", system_prompt),
            ("human", user_prompt)
        ]

    def execute_prompt(self, system_prompt: str, user_prompt: str, extract_json_output: bool = False) -> Optional[str]:
        if not self.is_safe_prompt(user_prompt) or not self.is_safe_prompt(system_prompt):
            print("LLMService: Potentially dangerous prompt, skipping execution")
            return None
        try:
            messages = self._get_messages(system_prompt, user_prompt)
            print('Invoking Claude...')
            result = self.model.invoke(messages)
            if extract_json_output:
                result = result.content
                # Try to extract JSON - handle nested structures
                # First try to find JSON block enclosed in ```json or similar
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
                if json_match:
                    result = json_match.group(1)
                else:
                    # Fallback to finding first complete JSON object (handles nested structures)
                    brace_count = 0
                    start_idx = result.find('{')
                    if start_idx != -1:
                        for i, char in enumerate(result[start_idx:], start_idx):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    result = result[start_idx:i+1]
                                    break
                        else:
                            # If no complete JSON found, try simple regex as fallback
                            match = re.search(r'\{[^{}]*\}', result)
                            result = match.group(0) if match else result
                return json.loads(result)
            return result.content
        except Exception as e:
            print(f"Error getting response: {e}")
            return None