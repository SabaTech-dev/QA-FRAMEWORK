#!/usr/bin/env python3
"""
Custom HTTP Provider for Promptfoo Red-Team — QA-FRAMEWORK
Sends adversarial prompts to QA-FRAMEWORK LLM endpoints and returns responses.

Usage: Referenced by promptfooconfig.yaml as file://./targets/qa-framework-http-provider.py
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.environ.get("QA_FRAMEWORK_BASE_URL", "http://localhost:8000")
AUTH_TOKEN = os.environ.get("QA_FRAMEWORK_JWT_TOKEN", "")


def call_api(prompt: str) -> str:
    """Send prompt to QA-FRAMEWORK evaluation endpoint."""
    url = f"{BASE_URL}/api/v1/evaluations"
    headers = {
        "Content-Type": "application/json",
    }
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    payload = json.dumps({
        "prompt": prompt,
        "model": "default",
    }).encode()

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            # Extract the LLM response from the evaluation result
            return data.get("result", data.get("output", str(data)))
    except urllib.error.HTTPError as e:
        return f"HTTP_ERROR:{e.code}:{e.reason}"
    except urllib.error.URLError as e:
        return f"URL_ERROR:{e.reason}"
    except Exception as e:
        return f"ERROR:{str(e)}"


def main():
    """Promptfoo calls this with the prompt on stdin."""
    prompt = sys.stdin.read().strip()
    if not prompt:
        print("ERROR: empty prompt")
        return
    result = call_api(prompt)
    print(result)


if __name__ == "__main__":
    main()
