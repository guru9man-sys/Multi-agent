"""
Enhanced Observability Dashboard - AgentOS
Real-time monitoring with DAG visualization, token analytics, and system health.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import DBManager
from datetime import datetime, timedelta
from sqlalchemy import func
import time

# Page Configuration
st.set_page_config(
    page_title="AgentOS Observability Dashboard",
    page_layout="wide",
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    [data-testid="metric.container"] { box-shadow: 0 0 1rem rgba(49, 51, 63, 0.15); padding: 1rem; border-radius: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# Initialize Database
@st.cache_resource
def init_db():
    return DBManager()

db = init_db()

# Page Title
st.title("🚀 AgentOS Observability Dashboard")
st.markdown("**Real-time Monitoring of Multi-Agent DAG Execution, Token Analytics & System Health**")

# --- Sidebar Configuration ---
st.sidebar.header("🎛️ Configuration")
refresh_interval = st.sidebar.slider("Auto-refresh (seconds)", 5, 60, 15)
selected_session = st.sidebar.text_input("Session ID", "default")
time_range = st.sidebar.radio("Time Range", ["Last Hour", "Last 24h", "All Time"], horizontal=True)

if st.sidebar.button("🔄 Refresh Now"):
    st.rerun()

# --- Helper Functions ---
def get_time_filter():
    if time_range == "Last Hour":
        return datetime.now() - timedelta(hours=1)
    elif time_range == "Last 24h":
        return datetime.now() - timedelta(days=1)
    return None

# --- KPI Metrics Row ---
st.subheader("📊 Key Performance Indicators")
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

# Fetch Global Metrics
try:
    total_tasks = db.query(func.count('tasks')).scalar() or 0
    total_tokens = db.get_total_token_usage() or 0
    avg_latency = db.get_average_execution_time() or 0
    success_rate = db.get_success_rate() or 0.0
    token_cost = (total_tokens / 1000) * 0.002  # Rough estimate: $0.002 per 1K tokens
    
    kpi_col1.metric("📋 Total Tasks", f"{total_tasks:,}")
    kpi_col2.metric("💾 Total Tokens", f"{total_tokens:,}")
    kpi_col3.metric("⏱️ Avg Latency", f"{avg_latency:.2f}s")
    kpi_col4.metric("✅ Success Rate", f"{success_rate*100:.1f}%")
    kpi_col5.metric("💰 Est. Cost", f"${token_cost:.2f}")
except Exception as e:
    st.warning(f"Error fetching KPI metrics: {e}")

st.divider()

# --- Main Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 DAG Flow", "💾 Token Analytics", "🛠️ System Health", "🔍 Deep Trace", "🕹️ CONTROL CENTER", "⚙️ Prompt Mgmt"])

with tab1:
    st.subheader("Active DAG Execution Flow")
    try:
        tasks = db.get_tasks_by_session(selected_session)
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            
            # Status Distribution
            col_status_left, col_status_right = st.columns(2)
            
            with col_status_left:
                status_count = df_tasks['status'].value_counts()
                fig_status = px.pie(
                    values=status_count.values,
                    names=status_count.index,
                    title="Task Status Distribution",
                    color_discrete_map={
                        "completed": "#28a745",
                        "in_progress": "#ffc107",
                        "failed": "#dc3545",
                        "pending": "#17a2b8"
                    }
                )
                st.plotly_chart(fig_status, use_container_width=True)
            
            with col_status_right:
                # Agent Workload
                agent_count = df_tasks['agent_role'].value_counts()
                fig_agents = px.bar(
                    x=agent_count.index,
                    y=agent_count.values,
                    title="Task Distribution by Agent",
                    labels={"x": "Agent", "y": "Tasks"}
                )
                st.plotly_chart(fig_agents, use_container_width=True)
            
            # Timeline Gantt Chart
            st.write("**Task Execution Timeline**")
            if 'created_at' in df_tasks.columns and 'updated_at' in df_tasks.columns:
                fig_gantt = px.timeline(
                    df_tasks,
                    x_start="created_at",
                    x_end="updated_at",
                    y="agent_role",
                    color="status",
                    hover_data=["task_id", "action"],
                    title="DAG Task Timeline"
                )
                st.plotly_chart(fig_gantt, use_container_width=True)
            
            # Detailed Task Table
            st.write("**Active Tasks**")
            df_display = df_tasks.copy()
            if 'created_at' in df_display.columns:
                df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%H:%M:%S')
            st.dataframe(df_display, use_container_width=True, height=400)
        else:
            st.info(f"No tasks found for session '{selected_session}'")
    except Exception as e:
        st.error(f"Error loading DAG flow: {e}")

with tab2:
    st.subheader("Token Consumption Analytics")
    try:
        metrics = db.get_execution_metrics_summary()
        if metrics:
            df_metrics = pd.DataFrame(metrics)
            
            # Token Usage by Agent
            col_token_left, col_token_right = st.columns(2)
            
            with col_token_left:
                token_by_agent = df_metrics.groupby("agent_role")[["prompt_tokens", "completion_tokens"]].sum().reset_index()
                token_by_agent["total"] = token_by_agent["prompt_tokens"] + token_by_agent["completion_tokens"]
                
                fig_tokens = px.bar(
                    token_by_agent,
                    x="agent_role",
                    y="total",
                    color="agent_role",
                    title="Total Tokens by Agent"
                )
                st.plotly_chart(fig_tokens, use_container_width=True)
            
            with col_token_right:
                # Token Cost Estimation
                token_by_agent["cost"] = token_by_agent["total"] * 0.000002  # $2 per 1M tokens
                fig_cost = px.pie(
                    values=token_by_agent["cost"],
                    names=token_by_agent["agent_role"],
                    title="Estimated Cost by Agent"
                )
                st.plotly_chart(fig_cost, use_container_width=True)
            
            # Token efficiency metrics
            st.write("**Efficiency Metrics**")
            df_efficiency = token_by_agent.copy()
            df_efficiency.columns = ["Agent", "Prompt", "Completion", "Total", "Cost"]
            st.dataframe(df_efficiency, use_container_width=True)
        else:
            st.info("No token metrics available")
    except Exception as e:
        st.error(f"Error loading token analytics: {e}")

with tab3:
    st.subheader("System Health & SRE Metrics")
    col_health_left, col_health_right = st.columns(2)
    
    try:
        with col_health_left:
            st.write("**Execution Performance**")
            perf_metrics = db.get_performance_metrics()
            if perf_metrics:
                df_perf = pd.DataFrame(perf_metrics)
                fig_perf = px.bar(
                    df_perf,
                    x="agent_role",
                    y="avg_duration",
                    title="Average Execution Time per Agent",
                    labels={"avg_duration": "Duration (seconds)"}
                )
                st.plotly_chart(fig_perf, use_container_width=True)
        
        with col_health_right:
            st.write("**Error Rate Trend**")
            error_trend = db.get_error_trend()
            if error_trend:
                df_error = pd.DataFrame(error_trend)
                fig_error = px.line(
                    df_error,
                    x="timestamp",
                    y="error_rate",
                    title="Error Rate Over Time"
                )
                st.plotly_chart(fig_error, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load health metrics: {e}")
    
    # SRE Report
    st.write("**Latest SRE Report**")
    try:
        sre_report = db.get_latest_sre_report()
        if sre_report:
            st.json(sre_report)
        else:
            st.info("No SRE reports available")
    except Exception as e:
        st.warning(f"Error loading SRE report: {e}")

with tab4:
    st.subheader("Deep Task Trace")
    try:
        # Task Selection
        all_tasks = db.get_all_task_ids()
        if all_tasks:
            selected_task_id = st.selectbox("Select Task ID", all_tasks)
            
            if selected_task_id:
                # Fetch trace
                task = db.get_task(selected_task_id)
                artifacts = db.get_artifacts(selected_task_id)
                logs = db.get_logs(selected_task_id)
                
                # Display trace information
                col_trace_info, col_trace_meta = st.columns(2)
                
                with col_trace_info:
                    st.write("**Task Information**")
                    if task:
                        st.json({
                            "task_id": task.task_id,
                            "agent_role": task.agent_role,
                            "action": task.action,
                            "status": task.status,
                            "priority": task.priority,
                            "created_at": str(task.created_at),
                            "updated_at": str(task.updated_at)
                        })
                
                with col_trace_meta:
                    st.write("**Task Artifacts**")
                    if artifacts:
                        for artifact in artifacts:
                            st.json({
                                "artifact_id": artifact.artifact_id,
                                "confidence": artifact.confidence,
                                "created_at": str(artifact.created_at)
                            })
                
                # Execution Logs
                st.write("**Execution Logs**")
                if logs:
                    df_logs = pd.DataFrame([
                        {
                            "timestamp": l.created_at,
                            "transition": f"{l.old_status} → {l.new_status}",
                            "reason": l.reason
                        }
                        for l in logs
                    ])
                    st.table(df_logs)
                else:
                    st.info("No logs found for this task")
        else:
            st.info("No tasks available")
    except Exception as e:
        st.error(f"Error loading deep trace: {e}")

with tab5:
    st.header("🕹️ Agent Control Center")
    st.markdown("Directly manage agent execution, modify instructions, and control session state.")
    
    API_BASE = "http://localhost:8000"
    
    # --- SECTION 1: Approval Gate ---
    st.subheader("1️⃣ Approval Gate")
    try:
        # Fetch tasks waiting for approval
        all_tasks = db.get_tasks_by_status("waiting_for_approval")
        if all_tasks:
            st.warning(f"⏳ {len(all_tasks)} task(s) waiting for approval")
            
            # Select task to approve/reject
            task_ids = [t.task_id for t in all_tasks]
            selected_approval_task = st.selectbox("Select Task to Review", task_ids)
            
            # Show task details
            task_detail = db.get_task(selected_approval_task)
            st.info(f"**Agent:** {task_detail.agent_role} | **Action:** {task_detail.action}")
            
            col_app_1, col_app_2 = st.columns(2)
            with col_app_1:
                if st.button("✅ APPROVE", use_container_width=True, type="primary"):
                    res = requests.post(f"{API_BASE}/control/execute", 
                                     json={"task_id": selected_approval_task, "action": "approve"})
                    if res.status_code == 200:
                        st.success("Task approved!")
                        st.rerun()
            with col_app_2:
                if st.button("❌ REJECT", use_container_width=True):
                    res = requests.post(f"{API_BASE}/control/execute", 
                                     json={"task_id": selected_approval_task, "action": "reject"})
                    if res.status_code == 200:
                        st.error("Task rejected!")
                        st.rerun()
        else:
            st.success("✅ No approval requests pending")
    except Exception as e:
        st.error(f"Approval Gate Error: {e}")

    st.divider()

    # --- SECTION 2: Task Modification ---
    st.subheader("2️⃣ Task Modification")
    try:
        # Fetch pending/in-progress tasks
        pending_tasks = db.get_tasks_by_status("pending") + db.get_tasks_by_status("in_progress")
        if pending_tasks:
            mod_task_ids = [t.task_id for t in pending_tasks]
            selected_mod_task = st.selectbox("Select Task to Modify", mod_task_ids)
            
            # Current Instruction
            task_obj = db.get_task(selected_mod_task)
            current_instr = (task_obj.payload or {}).get("instruction", "No instruction found")
            st.text_area("Current Instruction", value=current_instr, disabled=True)
            
            # New Instruction
            new_instr = st.text_area("Edit Instruction", placeholder="Enter new instructions for the agent...")
            if st.button("🔄 UPDATE INSTRUCTION", use_container_width=True):
                if new_instr:
                    res = requests.post(f"{API_BASE}/control/execute", 
                                     json={"task_id": selected_mod_task, "action": "update_instruction", 
                                           "payload": {"instruction": new_instr}})
                    if res.status_code == 200:
                        st.success("Instruction updated successfully!")
                        st.rerun()
                else:
                    st.warning("Please enter a new instruction")
        else:
            st.info("No pending tasks available for modification")
    except Exception as e:
        st.error(f"Modification Error: {e}")

    st.divider()

    # --- SECTION 3: Priority Control ---
    st.subheader("3️⃣ Priority Control")
    try:
        # Fetch all active tasks
        active_tasks = db.get_tasks_by_status("pending") + db.get_tasks_by_status("in_progress")
        if active_tasks:
            prio_task_ids = [t.task_id for t in active_tasks]
            selected_prio_task = st.selectbox("Select Task for Priority Change", prio_task_ids)
            
            new_prio = st.select_slider("Set Priority", options=["LOW", "MEDIUM", "HIGH"], value="MEDIUM")
            if st.button("⬆️ SET PRIORITY", use_container_width=True):
                # Note: api_server.py currently handles priority via DBManager directly or a specific endpoint
                # We'll use the /control/execute pattern if we add a priority action, 
                # or a direct DB update for now as a shortcut.
                res = requests.post(f"{API_BASE}/control/execute", 
                                  json={"task_id": selected_prio_task, "action": "update_priority", 
                                        "payload": {"priority": new_prio}})
                # If the endpoint doesn't exist yet, we'll handle it gracefully
                if res.status_code == 200:
                    st.success(f"Priority updated to {new_prio}")
                else:
                    st.error("Priority update endpoint not yet fully implemented in api_server.py")
        else:
            st.info("No active tasks available for priority control")
    except Exception as e:
        st.error(f"Priority Error: {e}")

    st.divider()

    # --- SECTION 4: Session Management ---
    st.subheader("4️⃣ Session Management")
    col_sess_1, col_sess_2 = st.columns([3, 1])
    with col_sess_1:
        st.write(f"**Current Active Session:** `{selected_session}`")
    with col_sess_2:
        if st.button("🔄 RESET SESSION", use_container_width=True, type="secondary"):
            res = requests.post(f"{API_BASE}/control/session", 
                              json={"task_id": selected_session, "action": "reset_session"})
            if res.status_code == 200:
                st.success("Session memory cleared!")
                st.rerun()

# --- New Tab: Prompt Management ---
import requests

with tab6:
    st.header("⚙️ Agent Prompt Management")
    st.markdown("View and edit system prompts for all agents in real-time. Changes take immediate effect.")
    
    API_BASE = "http://localhost:8000"
    
    try:
        # Fetch available agents
        agents_response = requests.get(f"{API_BASE}/agents/list", timeout=5)
        if agents_response.status_code != 200:
            st.error("Failed to fetch agents list")
        else:
            agents_list = list(agents_response.json().get("agents", {}).keys())
            
            if not agents_list:
                st.warning("No agents available")
            else:
                # Agent selector
                col_select, col_refresh = st.columns([3, 1])
                
                with col_select:
                    selected_agent = st.selectbox(
                        "🤖 Select Agent",
                        agents_list,
                        key="agent_selector"
                    )
                
                with col_refresh:
                    if st.button("🔄 Refresh", key="refresh_agent_config"):
                        st.rerun()
                
                # Fetch current agent config
                config_response = requests.get(f"{API_BASE}/agents/{selected_agent}/config", timeout=5)
                
                if config_response.status_code == 200:
                    config = config_response.json()
                    
                    # Display current config info
                    col_info_left, col_info_right, col_info_version = st.columns(3)
                    
                    with col_info_left:
                        st.metric("Agent Role", config["agent_role"])
                    
                    with col_info_right:
                        st.metric("Temperature", f"{config.get('temperature', 0.7):.1f}")
                    
                    with col_info_version:
                        st.metric("Version", config.get("version", 1))
                    
                    st.divider()
                    
                    # System prompt editor
                    st.write("**System Prompt**")
                    current_prompt = config.get("system_prompt", "")
                    
                    # Tabs for editing vs viewing
                    editor_tab, preview_tab = st.tabs(["✏️ Edit", "📄 Preview"])
                    
                    with editor_tab:
                        new_prompt = st.text_area(
                            "Edit system prompt",
                            value=current_prompt,
                            height=200,
                            key="prompt_editor"
                        )
                        
                        st.write("**Additional Parameters**")
                        col_param_left, col_param_right = st.columns(2)
                        
                        with col_param_left:
                            max_tokens = st.number_input(
                                "Max Tokens",
                                value=config.get("max_tokens", 2000),
                                min_value=100,
                                max_value=4000,
                                step=100
                            )
                        
                        with col_param_right:
                            temperature = st.slider(
                                "Temperature",
                                min_value=0.0,
                                max_value=2.0,
                                value=config.get("temperature", 0.7),
                                step=0.1
                            )
                        
                        # Action buttons
                        col_btn_save, col_btn_cancel, col_btn_rollback = st.columns(3)
                        
                        with col_btn_save:
                            if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                                update_payload = {
                                    "agent_role": selected_agent,
                                    "system_prompt": new_prompt,
                                    "max_tokens": max_tokens,
                                    "temperature": temperature
                                }
                                
                                update_response = requests.post(
                                    f"{API_BASE}/agents/{selected_agent}/config",
                                    json=update_payload,
                                    timeout=5
                                )
                                
                                if update_response.status_code == 200:
                                    st.success(f"✅ Configuration updated for {selected_agent}")
                                    st.json(update_response.json())
                                else:
                                    st.error(f"Failed to update configuration: {update_response.text}")
                        
                        with col_btn_cancel:
                            if st.button("❌ Discard", use_container_width=True):
                                st.info("Changes discarded")
                        
                        with col_btn_rollback:
                            if st.button("⏮️ Rollback", use_container_width=True):
                                rollback_response = requests.post(
                                    f"{API_BASE}/agents/{selected_agent}/config/rollback",
                                    timeout=5
                                )
                                
                                if rollback_response.status_code == 200:
                                    st.warning(f"⏮️ Configuration rolled back for {selected_agent}")
                                    st.json(rollback_response.json())
                                else:
                                    st.error("Failed to rollback configuration")
                    
                    with preview_tab:
                        st.markdown(current_prompt if current_prompt else "_No prompt configured_")
                else:
                    st.error("Failed to load agent configuration")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API server. Make sure api_server.py is running on localhost:8000")
    except Exception as e:
        st.error(f"Error in prompt management: {e}")

# Auto-refresh
st.markdown(f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")

# Placeholder for auto-refresh (Streamlit limitation - requires re-run)
time.sleep(0.1)  # Minimal delay

# --- Footer ---
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | AgentOS Observability v2.0")
