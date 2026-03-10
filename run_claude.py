import asyncio, argparse, json, os
from typing import Any
from claude_agent_sdk import query, ClaudeAgentOptions

# If needed to run this in a Docker, try using session token to authenticate by running following command
# After session token generated, uncomment line 8-13
# aws sts get-session-token --duration-seconds 3600 > session.json
# with open("./session.json", 'r') as f:
#     token = json.loads(f.read())

# os.environ['AWS_ACCESS_KEY_ID'] = token['Credentials']['AccessKeyId']
# os.environ['AWS_SECRET_ACCESS_KEY'] = token['Credentials']['SecretAccessKey']
# os.environ['AWS_SESSION_TOKEN'] = token['Credentials']['SessionToken']
os.environ['CLAUDE_CODE_USE_BEDROCK']='1'
os.environ['AWS_REGION']='us-east-1'

class Logger:
    def __init__(self, path):
        self.path = path

    def log(self, content: Any):
        with open(self.path, 'a') as f:
            f.write(f"{content}")

def parse_args():
    parser = argparse.ArgumentParser(description='Run Claude Code')
    parser.add_argument('--prompt', type=str, help='Prompt')
    parser.add_argument('--output_path', type=str, help='Log output path')
    return parser.parse_args()

async def main():
    args = parse_args()
    logger = Logger(args.output_path or "./output.log")
    options = ClaudeAgentOptions(
        model='global.anthropic.claude-sonnet-4-5-20250929-v1:0',
        system_prompt="You are an expert Python developer. "
        "CRITICAL: When using tools like Bash, Read, or Grep, you MUST limit your output. "
        "Do not read entire large files at once. Use `head`, `tail`, or read specific line ranges. "
        "Limit command outputs to avoid returning more than 500KB of text in a single tool response.",
        allowed_tools=['Task', 'TaskOutput', 'Bash', 'Glob', 'Grep', 'ExitPlanMode', 'Read', 'Edit', 'Write', 'NotebookEdit', 'TodoWrite', 'KillShell', 'Skill', 'EnterPlanMode', 'ToolSearch'],
        permission_mode='acceptEdits',
        cwd=os.getcwd(),
        max_turns=100  # Limit to 50 agentic rounds
        # max_budget_usd=1.00  # Stop if costs exceed $1.00
    )

    async for message in query(
        prompt=args.prompt,
        options=options
    ):
        msg_type = type(message).__name__
        
        # Filter and format different message types
        if msg_type == "SystemMessage":
            logger.log(f"\n[SYSTEM] Session: {message.data.get('session_id', 'N/A')}")
            logger.log(f"[SYSTEM] Model: {message.data.get('model', 'N/A')}")
            logger.log(f"[SYSTEM] Tools: {len(message.data.get('tools', []))} available")
            
        elif msg_type == "AssistantMessage":
            if message.content:
                for block in message.content:
                    if hasattr(block, 'text'):
                        logger.log(f"\n[CLAUDE] {block.text}")
                    elif hasattr(block, 'name'):  # ToolUseBlock
                        tool_name = block.name
                        tool_input = block.input
                        logger.log(f"\n[TOOL] {tool_name}")
                        # logger.log each parameter
                        for key, value in tool_input.items():
                            value_str = str(value)
                            logger.log(f"  - {key}: {value_str}")
                        
        elif msg_type == "UserMessage":
            # Tool results - usually verbose, so summarize
            for block in message.content:
                if hasattr(block, 'tool_use_id'):
                    is_error = block.is_error
                    status = "ERROR" if is_error else "SUCCESS"
                    content = str(block.content)
                    logger.log(f"[{status}] Tool result: {content}...")
                    
        elif msg_type == "ResultMessage":
            logger.log("\n" + "=" * 80 + "\n")
            logger.log(f"[RESULT] Status: {'ERROR' if message.is_error else 'SUCCESS'}\n")
            logger.log(f"[RESULT] Turns: {message.num_turns}\n")
            logger.log(f"[RESULT] Duration: {message.duration_ms}ms\n")
            logger.log(f"[RESULT] Cost: ${message.total_cost_usd:.4f}\n")
            if message.result:
                logger.log(f"[RESULT] Output: {message.result}\n")
            logger.log("=" * 80)


asyncio.run(main())