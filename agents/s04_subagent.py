#!/usr/bin/env python3
# Harness: context isolation -- protecting the model's clarity of thought.
"""
s04_subagent.py - Subagents

Spawn a child agent with fresh messages=[]. The child works in its own
context, sharing the filesystem, then returns only a summary to the parent.

    Parent agent                     Subagent
    +------------------+             +------------------+
    | messages=[...]   |             | messages=[]      |  <-- fresh
    |                  |  dispatch   |                  |
    | tool: task       | ---------->| while tool_use:  |
    |   prompt="..."   |            |   call tools     |
    |   description="" |            |   append results |
    |                  |  summary   |                  |
    |   result = "..." | <--------- | return last text |
    +------------------+             +------------------+
              |
    Parent context stays clean.
    Subagent context is discarded.

Key insight: "Process isolation gives context isolation for free."
"""

import json
import os
import subprocess
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()

# client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
client = OpenAI(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为: api_key="sk-xxx",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL"),
)
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use the task tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."


# -- Tool implementations shared by parent and child --
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

def run_read(path: str, limit: int = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
}

# Child gets all base tools except task (no recursive spawning)
CHILD_TOOLS = [
  {
    "type": "function",
    "function": {
      "name": "bash",
      "description": "Run a shell command.",
      "parameters": {
        "type": "object",
        "properties": { "command": { "type": "string" } },
        "required": ["command"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "read_file",
      "description": "Read file contents.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "limit": { "type": "integer" }
        },
        "required": ["path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "write_file",
      "description": "Write content to file.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "content": { "type": "string" }
        },
        "required": ["path", "content"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "edit_file",
      "description": "Replace exact text in file.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "old_text": { "type": "string" },
          "new_text": { "type": "string" }
        },
        "required": ["path", "old_text", "new_text"]
      }
    }
  }
]


# -- Subagent: fresh context, filtered tools, summary-only return --
def run_subagent(prompt: str) -> str:
    # Start with a fresh context but include the subagent system prompt
    sub_messages = [
        {"role": "system", "content": SUBAGENT_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    for _ in range(30):  # safety limit
        # print sub_messages
        # print("\033[32msubagent >>\033[0m", sub_messages[-1]["content"][:80])
        response = client.chat.completions.create(
            model=MODEL, messages=sub_messages,
            tools=CHILD_TOOLS, max_tokens=8000,
        )
        # print("called subagent:", response)
        choice = response.choices[0]
        assistant = choice.message
        assistant_message = {
            "role": "assistant",
            "content": assistant.content or "",
        }
        if assistant.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant.tool_calls
            ]
        sub_messages.append(assistant_message)
        if not assistant.tool_calls:
            break
        results = []
        for tc in assistant.tool_calls:
            handler = TOOL_HANDLERS.get(tc.function.name)
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = {}
            output = handler(**tool_input) if handler else f"Unknown tool: {tc.function.name}"
            results.append({"role": "tool", "tool_call_id": tc.id, "content": str(output)[:50000]})
        # API expects message content to be text (or structured types with 'type').
        # Serialize tool results to JSON so we don't pass a raw Python list.
        sub_messages.append({"role": "user", "content": json.dumps(results)})
    # Only the final text returns to the parent -- child context is discarded
    print("return response")
    return response;
    # # Prefer the last assistant message from the subagent conversation.
    # for msg in reversed(sub_messages):
    #     if msg.get("role") == "assistant":
    #         content = msg.get("content") or ""
    #         if isinstance(content, str):
    #             return content
    #         # If the content is a structured list of chunks, try to join text fields
    #         if isinstance(content, list):
    #             try:
    #                 return "".join(getattr(chunk, "text", str(chunk)) for chunk in content)
    #             except Exception:
    #                 return str(content)
    #         return str(content)
    # return "(no summary)"


# -- Parent tools: base tools + task dispatcher --
PARENT_TOOLS = CHILD_TOOLS + [
  {
    "type": "function",
    "function": {
      "name": "task",
      "description": "Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
      "parameters": {
        "type": "object",
        "properties": {
          "prompt": { "type": "string" },
          "description": {
            "type": "string",
            "description": "Short description of the task"
          }
        },
        "required": ["prompt"]
      }
    }
  }
]


def agent_loop(messages: list):
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=PARENT_TOOLS,
            max_tokens=8000,
        )
        choice = response.choices[0]
        assistant = choice.message
        assistant_message = {
            "role": "assistant",
            "content": assistant.content or "",
        }
        if assistant.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant.tool_calls
            ]
        messages.append(assistant_message)
        # If the model didn't call a tool, we're done
        if not assistant.tool_calls:
            return assistant.content or ""
        results = []
        for tc in assistant.tool_calls:
            if tc.function.name == "task":
                try:
                    tool_input = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                
                desc = tool_input.get("description", "subtask")
                prompt = tool_input.get("prompt", "")
                print(f"> task ({desc}): {prompt[:80]}")
                output = run_subagent(prompt)
            else:
                handler = TOOL_HANDLERS.get(tc.function.name)
                try:
                    tool_input = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                output = handler(**tool_input) if handler else f"Unknown tool: {tc.function.name}"
                print(str(output)[:200])
                results.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(output),
                })
        # Serialize tool results before appending to avoid passing raw lists
        messages.append({"role": "user", "content": json.dumps(results)})


if __name__ == "__main__":
    history = [{"role": "system", "content": SYSTEM}]
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        # print("before agent_loop, history:", history)
        agent_loop(history)
        # print("agent_loop returned, history:", history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
