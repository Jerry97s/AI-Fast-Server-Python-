# AI Agent using LangGraph and OpenAI with persistent memory

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from typing import TypedDict, Annotated
import operator
import json
import os

# Load environment variables
load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Memory file (프로젝트 루트 고정 — API·다른 cwd에서 실행해도 동일 파일 사용)
MEMORY_FILE = os.path.join(_PROJECT_ROOT, "memory.json")

def load_memory():
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"user_profile": {}, "preferences": {}, "history": [], "tasks": [], "knowledge": []}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Memory tools
@tool
def memory_save(key: str, value: str) -> str:
    """Save information to memory. Key should be in format like 'user_profile.name'."""
    data = load_memory()
    keys = key.split('.')
    current = data
    for k in keys[:-1]:
        current = current.setdefault(k, {})
    current[keys[-1]] = value
    save_memory(data)
    return f"Saved {key}: {value}"

@tool
def memory_load(key: str) -> str:
    """Load information from memory."""
    data = load_memory()
    keys = key.split('.')
    current = data
    try:
        for k in keys:
            current = current[k]
        return str(current)
    except KeyError:
        return f"Key {key} not found"

@tool
def memory_search(query: str) -> str:
    """Search memory for information containing the query."""
    data = load_memory()
    results = []
    def search_dict(d, path=""):
        for k, v in d.items():
            current_path = f"{path}.{k}" if path else k
            if query.lower() in current_path.lower() or (isinstance(v, str) and query.lower() in v.lower()):
                results.append(f"{current_path}: {v}")
            if isinstance(v, dict):
                search_dict(v, current_path)
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, str) and query.lower() in item.lower():
                        results.append(f"{current_path}[{i}]: {item}")
    search_dict(data)
    return "\n".join(results) if results else "No matches found"

# Log dir: 프로젝트(main.py 위치) 기준
CURRENT_LOG_DIR = [os.path.join(_PROJECT_ROOT, "logs")]  # set_log_directory로 덮어쓸 수 있음
READ_LOG_MAX_CHARS = 32000
os.makedirs(CURRENT_LOG_DIR[0], exist_ok=True)

@tool
def set_log_directory(folder_path: str) -> str:
    """Set the folder to analyze log files. Provide the folder path."""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(folder_path)
        
        # Check if path exists
        if not os.path.exists(abs_path):
            return f"폴더를 찾을 수 없습니다: {folder_path}"
        
        # Check if it's a directory
        if not os.path.isdir(abs_path):
            return f"이것은 폴더가 아닙니다: {folder_path}"
        
        # Set the new directory
        CURRENT_LOG_DIR[0] = abs_path
        return f"로그 분석 폴더가 설정되었습니다: {abs_path}"
    except Exception as e:
        return f"폴더 설정 오류: {str(e)}"

@tool
def read_log_file(filename: str) -> str:
    """현재 로그 폴더의 파일 전체 내용을 읽는다. 경로 없이 파일명만 넣는다.

    로그를 정리·요약해달라는 요청에는 이 도구로 전체 텍스트를 가져온 뒤,
    특정 단어(ERROR 등)만 찾아 나열하지 말고 시간 순서대로 무슨 일이 있었는지 한글로 정리해서 답한다."""
    try:
        base_dir = os.path.abspath(CURRENT_LOG_DIR[0])
        safe_name = os.path.basename(filename.strip().strip('"').strip("'"))
        filepath = os.path.abspath(os.path.join(base_dir, safe_name))
        try:
            if os.path.commonpath([filepath, base_dir]) != base_dir:
                return f"폴더 외부 파일에 접근할 수 없습니다: {base_dir}"
        except ValueError:
            return f"폴더 외부 파일에 접근할 수 없습니다: {base_dir}"
        
        if not os.path.exists(filepath):
            listing = ""
            if os.path.isdir(base_dir):
                names = sorted(os.listdir(base_dir))
                listing = "\n이 폴더의 파일: " + (", ".join(names) if names else "(비어 있음)")
            return (
                f"파일을 찾을 수 없습니다: {safe_name}\n"
                f"조회한 전체 경로: {filepath}\n"
                f"현재 로그 폴더: {base_dir}"
                + listing
            )
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if len(content) > READ_LOG_MAX_CHARS:
            head = content[:READ_LOG_MAX_CHARS]
            return (
                f"[앞부분만 표시: 총 {len(content)}자 중 {READ_LOG_MAX_CHARS}자까지]\n\n"
                + head
            )
        return content
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"

@tool
def list_log_files() -> str:
    """현재 설정된 로그 폴더 안의 파일 목록을 보여준다."""
    try:
        base_dir = os.path.abspath(CURRENT_LOG_DIR[0])
        header = f"로그 폴더: {base_dir}\n\n"
        if not os.path.exists(base_dir):
            return header + "해당 경로가 없습니다."
        
        files = os.listdir(base_dir)
        if not files:
            return header + "이 폴더는 비어 있습니다."
        
        file_info = []
        for f in files:
            filepath = os.path.join(base_dir, f)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                file_info.append(f"{f} ({size} bytes)")
        
        return header + ("\n".join(file_info) if file_info else "파일이 없습니다(폴더만 있음)")
    except Exception as e:
        return f"파일 목록 조회 오류: {str(e)}"

# Define a simple tool
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Define state
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# System prompt
system_prompt = """
You are a helpful AI agent with persistent memory capabilities.

You can save and load information using the memory tools:
- memory_save(key, value): Save important information
- memory_load(key): Retrieve specific information
- memory_search(query): Search for related information

Always consider the user's history, preferences, and previous interactions when responding.
Store important information like user preferences, project details, and conversation history.
Personalize your responses based on stored memory.

For example:
- If user mentions their name, save it to user_profile.name
- If user asks about previous topics, use memory_search or memory_load
- Remember user preferences and reference them in future responses
"""

# Initialize the LLM
llm = ChatOpenAI(temperature=0.7)
tools = [calculator, memory_save, memory_load, memory_search, set_log_directory, read_log_file, list_log_files]
llm_with_tools = llm.bind_tools(tools)

# Define nodes
def call_model(state):
    messages = state["messages"]
    # Check if system message already exists
    has_system = any(isinstance(msg, SystemMessage) for msg in messages)
    if not has_system:
        # Add Korean system prompt at the beginning
        system_message = SystemMessage(content=(
            "너는 한글로만 답변해야 한다. 절대 영어로 답하지 말고, 항상 한글로 답변하거나 사용자 요청에 맞는 정보만 제공한다. 당신의 이름은 AI 어시스턴트이고, 사용자를 돕기 위해 여기있다.\n\n"
            "로그 파일을 다룰 때: read_log_file로 받은 내용을 바탕으로 시간 순서대로 무슨 일이 있었는지 요약·정리한다. "
            "ERROR·WARNING 같은 특정 키워드만 골라 나열하지 말고, 전체 흐름을 설명한다."
        ))
        messages = [system_message] + messages

    # --- Safety/Robustness: 컨텍스트 길이 초과 방지 ---
    # 1) 너무 긴 대화는 최근 것만 유지
    MAX_MESSAGES = 20
    if len(messages) > MAX_MESSAGES:
        # system 메시지가 있으면 유지하고 최근 메시지만 잘라냄
        sys_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_sys = [m for m in messages if not isinstance(m, SystemMessage)]
        messages = (sys_msgs[:1] + non_sys[-(MAX_MESSAGES - 1):]) if sys_msgs else non_sys[-MAX_MESSAGES:]

    # 2) 개별 메시지 본문이 지나치게 길면 잘라냄(파일 업로드/대용량 텍스트 방지)
    MAX_HUMAN_CHARS = 4000
    MAX_TOOL_CHARS = 2000
    trimmed = []
    for m in messages:
        if isinstance(m, HumanMessage) and isinstance(m.content, str) and len(m.content) > MAX_HUMAN_CHARS:
            trimmed.append(
                HumanMessage(
                    content=(
                        m.content[:MAX_HUMAN_CHARS]
                        + "\n\n[중요] 입력이 너무 길어서 앞부분만 전달되었습니다. "
                        + "파일 내용은 업로드/저장 후 read_log_file 등 도구로 읽어 요약하도록 해주세요."
                    )
                )
            )
        elif isinstance(m, ToolMessage) and isinstance(m.content, str) and len(m.content) > MAX_TOOL_CHARS:
            trimmed.append(
                ToolMessage(
                    content=(
                        m.content[:MAX_TOOL_CHARS]
                        + "\n\n[중요] 도구 결과가 너무 길어서 앞부분만 전달되었습니다."
                    ),
                    tool_call_id=m.tool_call_id,
                )
            )
        else:
            trimmed.append(m)
    messages = trimmed

    # 3) 총 글자수도 상한을 둬서(툴 결과 누적) 컨텍스트 폭발 방지
    #    오래된 non-system 메시지부터 제거
    def _msg_len(x) -> int:
        c = getattr(x, "content", "")
        return len(c) if isinstance(c, str) else len(str(c))

    MAX_TOTAL_CHARS = 14000
    sys_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    non_sys = [m for m in messages if not isinstance(m, SystemMessage)]
    total = sum(_msg_len(m) for m in non_sys)
    while total > MAX_TOTAL_CHARS and len(non_sys) > 1:
        dropped = non_sys.pop(0)
        total -= _msg_len(dropped)
    messages = (sys_msgs[:1] + non_sys) if sys_msgs else non_sys

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def call_tools(state):
    messages = state["messages"]
    last_message = messages[-1]
    tool_calls = last_message.tool_calls
    results = []
    for tool_call in tool_calls:
        if tool_call["name"] == "calculator":
            result = calculator.invoke(tool_call["args"])
        elif tool_call["name"] == "memory_save":
            result = memory_save.invoke(tool_call["args"])
        elif tool_call["name"] == "memory_load":
            result = memory_load.invoke(tool_call["args"])
        elif tool_call["name"] == "memory_search":
            result = memory_search.invoke(tool_call["args"])
        elif tool_call["name"] == "read_log_file":
            result = read_log_file.invoke(tool_call["args"])
        elif tool_call["name"] == "list_log_files":
            result = list_log_files.invoke(tool_call["args"])
        elif tool_call["name"] == "set_log_directory":
            result = set_log_directory.invoke(tool_call["args"])
        else:
            result = "Unknown tool"
        results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    return {"messages": results}

def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)
workflow.add_edge("tools", "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.set_entry_point("agent")

# 체크포인터를 SQLite로 저장하면 서비스 재시작 후에도 대화 문맥이 유지됩니다.
_CHECKPOINT_DB_PATH = os.path.join(_PROJECT_ROOT, "agent_checkpoint.db")
_checkpoint_conn = sqlite3.connect(_CHECKPOINT_DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(_checkpoint_conn)
app = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    print("AI Agent is ready! Ask me anything.")
    config = {"configurable": {"thread_id": "user_session"}}
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
        print(f"Agent: {result['messages'][-1].content}")
