"""
MCP Agent Web Interface
=======================

A Streamlit-based web UI for interacting with the MCP Agent.

This provides a visual way to see the agent loop in action,
making it easier to understand how the agent works.

Usage:
    streamlit run gui.py

Or via Docker:
    make gui
"""

import streamlit as st
import json
from agent import MCPAgent, EventType, AgentEvent

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="MCP Agent Lab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# Custom Styling
# =============================================================================

st.markdown("""
<style>
    /* Step indicators */
    .step-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
        margin-right: 8px;
    }
    .step-1 { background: #4361ee; color: white; }
    .step-2 { background: #7209b7; color: white; }
    .step-3 { background: #f72585; color: white; }
    .step-4 { background: #4cc9f0; color: black; }
    .step-5 { background: #4895ef; color: white; }
    .step-6 { background: #06d6a0; color: black; }

    /* Tool call cards */
    .tool-card {
        background: rgba(67, 97, 238, 0.1);
        border-left: 3px solid #4361ee;
        padding: 10px;
        margin: 5px 0;
        border-radius: 0 8px 8px 0;
        font-family: monospace;
    }

    /* Result cards */
    .result-card {
        background: rgba(6, 214, 160, 0.1);
        border-left: 3px solid #06d6a0;
        padding: 10px;
        margin: 5px 0;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Helper Functions (defined early so they can be used below)
# =============================================================================

STEP_NAMES = {
    1: "Discovery",
    2: "Reasoning",
    3: "Decision",
    4: "Execution",
    5: "Synthesis",
    6: "Answer"
}


def serialize_event(event: AgentEvent) -> dict:
    """Convert an AgentEvent to a serializable dict for session state."""
    return {
        "type": event.type.value,
        "step": event.step,
        "message": event.message,
        "data": event.data
    }


def deserialize_event(data: dict) -> AgentEvent:
    """Convert a dict back to an AgentEvent."""
    return AgentEvent(
        type=EventType(data["type"]),
        step=data["step"],
        message=data["message"],
        data=data.get("data")
    )


def render_history_event(event_data: dict):
    """Render a serialized event from chat history."""
    event = deserialize_event(event_data)

    if event.type == EventType.STEP_START:
        step_name = STEP_NAMES.get(event.step, "Unknown")
        st.markdown(f"**Step {event.step}: {step_name}** - {event.message}")

    elif event.type == EventType.INFO:
        st.write(f"  ℹ️ {event.message}")

    elif event.type == EventType.SUCCESS:
        st.write(f"  ✅ {event.message}")

    elif event.type == EventType.TOOL_CALL:
        if event.data:
            tool_name = event.data.get("name", "unknown")
            args = event.data.get("arguments", {})
            st.write(f"  🛠️ **{tool_name}**")
            if args:
                st.code(json.dumps(args, indent=2), language="json")
        else:
            st.write(f"  🛠️ {event.message}")

    elif event.type == EventType.TOOL_RESULT:
        if event.data:
            tool_name = event.data.get("tool", "unknown")
            result = str(event.data.get("result", ""))
            # Truncate long results
            if len(result) > 300:
                result = result[:300] + "..."
            st.write(f"  📤 Result from **{tool_name}**:")
            st.code(result)
        else:
            st.write(f"  📤 {event.message}")

    elif event.type == EventType.ERROR:
        st.error(f"❌ {event.message}")


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.title("🧪 MCP Lab")
    st.caption("Educational AI Agent Playground")

    st.divider()

    # Clear conversation button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Agent loop explanation
    st.subheader("The Agent Loop")
    st.markdown("""
    **1. Discovery** 🔍
    Find available tools

    **2. Reasoning** 🧠
    Send prompt to LLM

    **3. Decision** 🎯
    LLM chooses tools

    **4. Execution** ⚙️
    Run the tools

    **5. Synthesis** 📝
    Generate final answer
    """)

    st.divider()

    st.caption("Built for learning MCP and AI Agents")

# =============================================================================
# Main Chat Interface
# =============================================================================

st.title("🤖 MCP Agent Chat")
st.caption("Ask questions about files or the database")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show agent loop details in an expander for assistant messages
        if message["role"] == "assistant" and "events" in message and message["events"]:
            with st.expander("🔍 View Agent Loop Details", expanded=False):
                for event_data in message["events"]:
                    render_history_event(event_data)

# =============================================================================
# Chat Input Handler
# =============================================================================

if prompt := st.chat_input("Ask me something... (e.g., 'Who wrote the groceries note?')"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run the agent and display response
    with st.chat_message("assistant"):
        agent = MCPAgent()
        events = []
        final_answer = ""

        # Show progress
        with st.status("🤖 Agent is working...", expanded=True) as status:
            for event in agent.run(prompt):
                events.append(event)

                if event.type == EventType.STEP_START:
                    step_name = STEP_NAMES.get(event.step, "Unknown")
                    st.write(f"**Step {event.step}: {step_name}**")

                elif event.type == EventType.INFO:
                    st.write(f"  ℹ️ {event.message}")

                elif event.type == EventType.SUCCESS:
                    st.write(f"  ✅ {event.message}")

                elif event.type == EventType.TOOL_CALL:
                    tool_name = event.data.get("name", "unknown") if event.data else "unknown"
                    st.write(f"  🛠️ Calling: `{tool_name}`")

                elif event.type == EventType.TOOL_RESULT:
                    tool_name = event.data.get("tool", "unknown") if event.data else "unknown"
                    st.write(f"  📤 Got result from `{tool_name}`")

                elif event.type == EventType.FINAL_ANSWER:
                    final_answer = event.message
                    status.update(label="✨ Complete!", state="complete", expanded=False)

                elif event.type == EventType.ERROR:
                    st.error(event.message)
                    status.update(label="❌ Error", state="error")
                    final_answer = f"Error: {event.message}"

        # Display the final answer
        if final_answer:
            st.markdown(final_answer)

        # Store in session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_answer,
            "events": [serialize_event(e) for e in events]
        })
