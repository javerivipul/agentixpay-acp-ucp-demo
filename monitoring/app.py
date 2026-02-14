import streamlit as st
import subprocess
import time
import socket
import requests
from datetime import datetime

st.set_page_config(page_title="AgentixPay Service Monitor", page_icon="🔧", layout="wide")

VM_HOST = "agentixpay-n8n"
VM_ZONE = "us-east1-d"
VM_PROJECT = "agentixpay-sales-outreach"
DUCKDNS_DOMAIN = "agentixpay-demo.duckdns.org"

def run_gcloud_command(command):
    try:
        result = subprocess.run(
            f"gcloud compute ssh {VM_HOST} --zone={VM_ZONE} --project={VM_PROJECT} --command=\"{command}\"",
            shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def check_port_open(host, port, timeout=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def get_service_status():
    stdout, stderr, code = run_gcloud_command("sudo systemctl is-active n8n caddy docker")
    if code == 0:
        lines = stdout.strip().split('\n')
        return {name: status == 'active' for name, status in zip(['n8n', 'caddy', 'docker'], lines)}
    return {'n8n': False, 'caddy': False, 'docker': False}

def get_docker_status():
    stdout, _, code = run_gcloud_command("docker ps --format '{{.Names}}\t{{.Status}}'")
    if code == 0:
        containers = {}
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) == 2:
                    containers[parts[0]] = parts[1]
        return containers
    return {}

def get_service_ports():
    return {
        'chat-client': 3000,
        'merchant': 4001,
        'psp': 4000,
        'mcp-ui-server': 3112,
        'n8n': 5678,
    }

def check_url(url, timeout=5):
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        return response.status_code
    except:
        return None

st.title("🔧 AgentixPay Service Monitor")
st.markdown(f"**Domain:** https://{DUCKDNS_DOMAIN}")
st.markdown(f"**VM:** {VM_HOST} ({VM_ZONE})")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("🐳 Docker Containers")
    containers = get_docker_status()
    for name, status in containers.items():
        color = "🟢" if "Up" in status else "🔴"
        st.write(f"{color} {name}")

with col2:
    st.subheader("⚙️ System Services")
    services = get_service_status()
    for name, is_active in services.items():
        color = "🟢" if is_active else "🔴"
        st.write(f"{color} {name}")

with col3:
    st.subheader("🔌 Port Status")
    ports = get_service_ports()
    for service, port in ports.items():
        is_open = check_port_open(VM_HOST.replace('agentixpay-n8n', 'localhost'), port)
        color = "🟢" if is_open else "🔴"
        st.write(f"{color} {service} (:{port})")

with col4:
    st.subheader("🌐 URL Health")
    urls = {
        'n8n': f'https://{DUCKDNS_DOMAIN}/',
        'demo': f'https://{DUCKDNS_DOMAIN}/',
    }
    for name, url in urls.items():
        status = check_url(url)
        if status:
            color = "🟢" if status < 400 else "🟡"
            st.write(f"{color} {name} ({status})")
        else:
            st.write(f"🔴 {name} (error)")

st.divider()
st.subheader("📋 Service Details")

service_info = {
    'n8n': {'port': 5678, 'type': 'docker', 'description': 'n8n Workflow Automation'},
    'chat-client': {'port': 3000, 'type': 'nextjs', 'description': 'Chat UI'},
    'merchant': {'port': 4001, 'type': 'express', 'description': 'Merchant API'},
    'psp': {'port': 4000, 'type': 'express', 'description': 'Payment Service Provider'},
    'mcp-ui-server': {'port': 3112, 'type': 'express', 'description': 'MCP Server'},
}

cols = st.columns(5)
for i, (service, info) in enumerate(service_info.items()):
    with cols[i]:
        st.markdown(f"**{service}**")
        st.caption(info['description'])
        st.caption(f"Port: {info['port']}")
        st.caption(f"Type: {info['type']}")

st.divider()
st.subheader("🔄 Quick Actions")

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("Restart n8n"):
        with st.spinner("Restarting n8n..."):
            run_gcloud_command("sudo systemctl restart n8n")
            time.sleep(5)
        st.success("n8n restart initiated")

with c2:
    if st.button("Restart Caddy"):
        with st.spinner("Restarting Caddy..."):
            run_gcloud_command("sudo systemctl restart caddy")
            time.sleep(3)
        st.success("Caddy restart initiated")

with c3:
    if st.button("Restart Docker"):
        with st.spinner("Restarting Docker..."):
            run_gcloud_command("sudo systemctl restart docker")
            time.sleep(5)
        st.success("Docker restart initiated")

with c4:
    if st.button("Refresh Status"):
        st.rerun()

st.divider()
st.caption("Auto-refresh every 30 seconds")
if st.button("Enable Auto-Refresh"):
    import streamlit.runtime.scriptrunner as scriptrunner
    scriptrunner.magic_funcs.st_autorefresh(30)
