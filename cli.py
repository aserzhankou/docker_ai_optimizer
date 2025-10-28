#!/usr/bin/env python3
"""
Dockerfile AI Optimizer CLI

Usage:
    python cli.py -i Dockerfile -o optimized.Dockerfile
    python cli.py -i Dockerfile  # output to stdout
    cat Dockerfile | python cli.py  # read from stdin
    python cli.py -i Dockerfile -o /dev/stdout  # force stdout
"""

import argparse
import os
import sys
import requests
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def optimize_dockerfile(dockerfile_content: str, api_key: str, model: str = "gpt-5-mini") -> str:
    """Optimize Dockerfile using Abacus API and return only the optimized Dockerfile."""
    
    system_prompt = (
        "You are an expert DevOps assistant specialized in Dockerfile optimization. "
        "Return your response in exactly this format:\n\n"
        "```dockerfile\n[OPTIMIZED_DOCKERFILE_CONTENT]\n```\n\n"
        "---SUMMARY---\n"
        "[Brief summary of changes and optimizations made]\n\n"
        "Do not include any other text or explanations outside these sections."
    )

    user_prompt = f"""
Optimize the following Dockerfile for better performance, less layers, smaller image size, and faster build time.

Original Dockerfile:

```
{dockerfile_content}
```
"""

    url = "https://routellm.abacus.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 2000,
    }

    # Use session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        resp = session.post(url, headers=headers, json=payload, timeout=90)
        if resp.status_code >= 400:
            raise RuntimeError(f"API request failed: {resp.status_code} - {resp.text}")
        data = resp.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Request timeout - try with a simpler Dockerfile")
    except Exception as exc:
        raise RuntimeError(f"Abacus request failed: {exc}")

    content = ""
    try:
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
    except Exception:
        content = ""

    if not content:
        raise RuntimeError("Empty response from Abacus ChatLLM")

    # Extract only the Dockerfile content (ignore summary)
    dockerfile_content = ""
    try:
        # Split by summary separator and take only the first part
        parts = content.split("---SUMMARY---", 1)
        dockerfile_section = parts[0].strip()
        
        # Extract Dockerfile from fenced code block
        match = re.search(r"```(?:dockerfile)?\s*([\s\S]*?)```", dockerfile_section, re.IGNORECASE)
        if match:
            dockerfile_content = match.group(1).strip()
        else:
            # Fallback: extract from first FROM line
            lines = dockerfile_section.splitlines()
            start_idx = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("FROM ")), None)
            if start_idx is not None:
                dockerfile_content = "\n".join(lines[start_idx:]).strip()
    except Exception:
        dockerfile_content = content  # fallback to full content

    return dockerfile_content


def main():
    parser = argparse.ArgumentParser(
        description="Dockerfile AI Optimizer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py -i Dockerfile -o optimized.Dockerfile
  python cli.py -i Dockerfile  # output to stdout
  cat Dockerfile | python cli.py  # read from stdin
  python cli.py -i Dockerfile -o /dev/stdout  # force stdout
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        help="Input Dockerfile file path (default: read from stdin)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: write to stdout)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Abacus model to use (default: gpt-5-mini)"
    )
    
    parser.add_argument(
        "--api-key",
        help="Abacus API key (default: read from ABACUS_API_KEY env var)"
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("ABACUS_API_KEY")
    if not api_key:
        print("Error: ABACUS_API_KEY environment variable not set", file=sys.stderr)
        print("Set it with: export ABACUS_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    # Read input
    if args.input:
        try:
            with open(args.input, 'r') as f:
                dockerfile_content = f.read()
        except FileNotFoundError:
            print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        try:
            dockerfile_content = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nOperation cancelled", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    if not dockerfile_content.strip():
        print("Error: No Dockerfile content provided", file=sys.stderr)
        sys.exit(1)

    # Optimize
    try:
        print("Optimizing Dockerfile...", file=sys.stderr)
        optimized = optimize_dockerfile(dockerfile_content, api_key, args.model)
        
        # Write output
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    f.write(optimized)
                print(f"Optimized Dockerfile written to: {args.output}", file=sys.stderr)
            except Exception as e:
                print(f"Error writing to output file: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(optimized)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
