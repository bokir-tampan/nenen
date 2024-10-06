import os
import random
import subprocess
import json
import base64
import uuid
import sys
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

VALID_API_KEYS = ["meki"]

# Middleware untuk mengecek API Key pada setiap request
@app.before_request
def check_api_key():
    api_key = request.headers.get("Authorization")
    if api_key not in VALID_API_KEYS:
        logging.error("Unauthorized access attempt.")
        return jsonify({"error": "Unauthorized"}), 401

# Mengambil nilai domain dari file
def get_domain():
    with open('/etc/xray/domain', 'r') as file:
        return file.read().strip()

domain = get_domain()

def generate_vmess_config(user, uid, port, net, tls):
    config = {
        "v": "2",
        "ps": user,
        "add": domain,
        "port": port,
        "id": str(uid),
        "aid": "0",
        "net": net,
        "path": "/vmess",
        "type": "none",
        "host": domain,
        "tls": tls
    }
    return config

@app.route("/create-vmess")
def create_vmess():
    user = request.args.get("user")
    quota = request.args.get("quota")
    limit_ip = request.args.get("limitip")
    exp = request.args.get("exp")

    logging.debug(f"Received parameters: user={user}, quota={quota}, limit_ip={limit_ip}, exp={exp}")

    if not all([user, quota, limit_ip, exp]):
        logging.error("Missing parameters")
        return "Missing parameters", 400

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/paradis/paradis.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"User {user} already exists")
        return "User already exists", 400

    today = datetime.today()
    later = today + timedelta(days=exp)
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = (
            r'sed -i "/#vmess$/a\###ws {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" /etc/default/syncron/paradis/paradis.json'
            .format(user, later.strftime('%Y-%m-%d'), uid, uid, user)
        )
        subprocess.run(sed_command, shell=True, check=True)

        sed_command1 = (
            r'sed -i "/#grpcvmess$/a\###grpc {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" /etc/default/syncron/paradis/paradis.json'
            .format(user, later.strftime('%Y-%m-%d'), uid, uid, user)
        )
        subprocess.run(sed_command1, shell=True, check=True)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/vmess/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/vmess/{user}', shell=True, check=True)

        with open('/etc/.vmess', 'a') as vmess_file:
            vmess_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid}\n")

        subprocess.run(["systemctl", "restart", "paradis"], check=True)

        vmess_config_tls = generate_vmess_config(user, uid, "443", "ws", "tls")
        vmess_config_json_tls = json.dumps(vmess_config_tls)
        vmess_base64_tls = base64.urlsafe_b64encode(vmess_config_json_tls.encode()).decode()

        vmess_config_non = generate_vmess_config(user, uid, "80", "ws", "none")
        vmess_config_json_non = json.dumps(vmess_config_non)
        vmess_base64_non = base64.urlsafe_b64encode(vmess_config_json_non.encode()).decode()

        vmess_config_grpc = generate_vmess_config(user, uid, "443", "grpc", "tls")
        vmess_config_json_grpc = json.dumps(vmess_config_grpc)
        vmess_base64_grpc = base64.urlsafe_b64encode(vmess_config_json_grpc.encode()).decode()

        return {
            "vmess_base64_tls": "vmess://" + vmess_base64_tls,
            "vmess_base64_non": "vmess://" + vmess_base64_non,
            "vmess_base64_grpc": "vmess://" + vmess_base64_grpc
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return f"Error executing command: {e}", 500
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return f"An error occurred: {e}", 500

@app.route("/trial-vmess")
def trial_vmess():
    user = "trialX-" + str(random.randint(10, 1000))
    quota = "1"
    limit_ip = "1"
    exp = "1"

    logging.debug(f"Generated trial user: {user}")

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/paradis/paradis.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"Trial user {user} already exists")
        return "User already exists", 400

    today = datetime.now()
    later = today + timedelta(hours=exp)
    later1 = today + timedelta(days=exp)
    exp_timestamp = int(later.timestamp())
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = (
            r'sed -i "/#vmess$/a\###ws {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" /etc/default/syncron/paradis/paradis.json'
            .format(user, later.strftime('%Y-%m-%d'), uid, uid, user)
        )
        subprocess.run(sed_command, shell=True, check=True)

        sed_command1 = (
            r'sed -i "/#grpcvmess$/a\###grpc {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" /etc/default/syncron/paradis/paradis.json'
            .format(user, later.strftime('%Y-%m-%d'), uid, uid, user)
        )
        subprocess.run(sed_command1, shell=True, check=True)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/vmess/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/vmess/{user}', shell=True, check=True)

        with open('/etc/.vmess', 'a') as vmess_file:
            vmess_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid} {exp_timestamp}\n")

        subprocess.run(["systemctl", "restart", "paradis"], check=True)

        vmess_config_tls = generate_vmess_config(user, uid, "443", "ws", "tls")
        vmess_config_json_tls = json.dumps(vmess_config_tls)
        vmess_base64_tls = base64.urlsafe_b64encode(vmess_config_json_tls.encode()).decode()

        vmess_config_non = generate_vmess_config(user, uid, "80", "ws", "none")
        vmess_config_json_non = json.dumps(vmess_config_non)
        vmess_base64_non = base64.urlsafe_b64encode(vmess_config_json_non.encode()).decode()

        vmess_config_grpc = generate_vmess_config(user, uid, "443", "grpc", "tls")
        vmess_config_json_grpc = json.dumps(vmess_config_grpc)
        vmess_base64_grpc = base64.urlsafe_b64encode(vmess_config_json_grpc.encode()).decode()

        return {
            "vmess_base64_tls": "vmess://" + vmess_base64_tls,
            "vmess_base64_non": "vmess://" + vmess_base64_non,
            "vmess_base64_grpc": "vmess://" + vmess_base64_grpc
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return f"Error executing command: {e}", 500
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return f"An error occurred: {e}", 500

@app.route("/create-trojan")
def create_trojan():
    user = request.args.get("user")
    quota = request.args.get("quota")
    limit_ip = request.args.get("limitip")
    exp = request.args.get("exp")

    logging.debug(f"Received parameters: user={user}, quota={quota}, limit_ip={limit_ip}, exp={exp}")

    if not all([user, quota, limit_ip, exp]):
        logging.error("Missing parameters")
        return "Missing parameters", 400

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/drawit/drawit.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"User {user} already exists")
        return "User already exists", 400

    today = datetime.today()
    later = today + timedelta(days=exp)
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = r'sed -i "/#trojan$/a\###ws {} {} {}\\n}},{{\"password\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/drawit/drawit.json")
        logging.debug(f"Running command: {sed_command}")
        subprocess.run(sed_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sed_command1 = r'sed -i "/#grpctrojan$/a\###grpc {} {} {}\\n}},{{\"password\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/drawit/drawit.json")
        logging.debug(f"Running command: {sed_command1}")
        subprocess.run(sed_command1, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/trojan/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/trojan/{user}', shell=True, check=True)

        with open('/etc/.trojan', 'a') as trojan_file:
            trojan_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid}\n")

        subprocess.run(["systemctl", "restart", "drawit"], check=True)

        trojan_link = f"trojan://{uid}@bugkamu.com:443?path=%2Ftrojan-ws&security=tls&host={domain}&type=ws&sni={domain}#{user}"
        trojan_link1 = f"trojan://{uid}@{domain}:443?mode=gun&security=tls&type=grpc&serviceName=trojan&sni=bug.com#{user}"

        return {
            "trojan_link": trojan_link,
            "trojan_link1": trojan_link1
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return str(e), 500   
        
@app.route("/trial-trojan")
def trial_trojan():
    user = "trialX-" + str(random.randint(10, 1000))
    quota = "1"
    limit_ip = "1"
    exp = "1"

    logging.debug(f"Generated trial user: {user}")

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/drawit/drawit.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"Trial user {user} already exists")
        return "User already exists", 400

    today = datetime.now()
    later = today + timedelta(hours=exp)
    later1 = today + timedelta(days=exp)
    exp_timestamp = int(later.timestamp())
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = r'sed -i "/#trojan$/a\###ws {} {} {}\\n}},{{\"password\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/drawit/drawit.json")
        logging.debug(f"Running command: {sed_command}")
        subprocess.run(sed_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sed_command1 = r'sed -i "/#grpctrojan$/a\###grpc {} {} {}\\n}},{{\"password\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/drawit/drawit.json")
        logging.debug(f"Running command: {sed_command1}")
        subprocess.run(sed_command1, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/trojan/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/trojan/{user}', shell=True, check=True)

        with open('/etc/.trojan', 'a') as trojan_file:
            trojan_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid} {exp_timestamp}\n")

        subprocess.run(["systemctl", "restart", "drawit"], check=True)

        trojan_link = f"trojan://{uid}@bugkamu.com:443?path=%2Ftrojan-ws&security=tls&host={domain}&type=ws&sni={domain}#{user}"
        trojan_link1 = f"trojan://{uid}@{domain}:443?mode=gun&security=tls&type=grpc&serviceName=trojan&sni=bug.com#{user}"

        return {
            "trojan_link": trojan_link,
            "trojan_link1": trojan_link1
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return str(e), 500   
        
@app.route("/trial-vless")
def trial_vless():
    user = "trialX-" + str(random.randint(10, 1000))
    quota = "1"
    limit_ip = "1"
    exp = "1"

    logging.debug(f"Generated trial user: {user}")

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/sketsa/sketsa.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"Trial user {user} already exists")
        return "User already exists", 400

    today = datetime.now()
    later = today + timedelta(hours=exp)
    later1 = today + timedelta(days=exp)
    exp_timestamp = int(later.timestamp())
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = r'sed -i "/#vless$/a\###ws {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/sketsa/sketsa.json")
        logging.debug(f"Running command: {sed_command}")
        subprocess.run(sed_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sed_command1 = r'sed -i "/#grpcvless$/a\###grpc {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/sketsa/sketsa.json")
        logging.debug(f"Running command: {sed_command1}")
        subprocess.run(sed_command1, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/vless/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/vless/{user}', shell=True, check=True)

        with open('/etc/.vless', 'a') as vless_file:
            vless_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid} {exp_timestamp}\n")

        subprocess.run(["systemctl", "restart", "sketsa"], check=True)

        vless_link = f"vless://{uid}@bugkamu.com:443?path=%2Fvless&security=tls&host={domain}&type=ws&sni={domain}#{user}"
        vless_link1 = f"vless://{uid}@{domain}:443?mode=gun&security=tls&type=grpc&serviceName=vless&sni=bug.com#{user}"
        vless_link2 = f"vless://{uid}@bugkamu.com:80?path=%2Fvless&security=none&host={domain}&type=ws&sni={domain}#{user}"

        return {
            "vless_link": vless_link,
            "vless_link1": vless_link1,
            "vless_link2": vless_link2
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return str(e), 500   


#reneeeeeeew 

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.readlines()

def write_file(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)
        
@app.route("/renewvmess")
def renewvmess():
    masaaktif = int(request.args.get("exp"))
    user = request.args.get("user")
    vmess_file = '/etc/.vmess'
    paradis_file = '/etc/default/syncron/paradis/paradis.json'
    lines = read_file(vmess_file)
    user_line = next((line for line in lines if line.startswith(f"### {user} ")), None)
    if not user_line:
        return "User not found"
    exp = user_line.split()[2]
    now = datetime.now().strftime("%Y-%m-%d")
    current_exp_date = datetime.strptime(exp, "%Y-%m-%d")
    current_date = datetime.strptime(now, "%Y-%m-%d")
    delta_days = (current_exp_date - current_date).days
    new_exp_date = current_date + timedelta(days=delta_days + masaaktif)
    new_exp_str = new_exp_date.strftime("%Y-%m-%d")
    new_lines = [line.replace(f"### {user} {exp}", f"### {user} {new_exp_str}") if line.startswith(f"### {user} ") else line for line in lines]
    write_file(vmess_file, new_lines)
    
    paradis_lines = read_file(paradis_file)
    new_paradis_lines = []
    for line in paradis_lines:
        if line.startswith(f"###ws {user} {exp}"):
            new_line = line.replace(f"###ws {user} {exp}", f"###ws {user} {new_exp_str}")
        elif line.startswith(f"###grpc {user} {exp}"):
            new_line = line.replace(f"###grpc {user} {exp}", f"###grpc {user} {new_exp_str}")
        else:
            new_line = line
        new_paradis_lines.append(new_line)
    
    write_file(paradis_file, new_paradis_lines)
    
    return f"User {user} vmess extended to {new_exp_str}"

@app.route("/renewtrojan")
def renewtrojan():
    masaaktif = int(request.args.get("exp"))
    user = request.args.get("user")
    trojan_file = '/etc/.trojan'
    drawit_file = '/etc/default/syncron/drawit/drawit.json'
    lines = read_file(trojan_file)
    user_line = next((line for line in lines if line.startswith(f"### {user} ")), None)
    if not user_line:
        return "User not found"
    exp = user_line.split()[2]
    now = datetime.now().strftime("%Y-%m-%d")
    current_exp_date = datetime.strptime(exp, "%Y-%m-%d")
    current_date = datetime.strptime(now, "%Y-%m-%d")
    delta_days = (current_exp_date - current_date).days
    new_exp_date = current_date + timedelta(days=delta_days + masaaktif)
    new_exp_str = new_exp_date.strftime("%Y-%m-%d")
    new_lines = [line.replace(f"### {user} {exp}", f"### {user} {new_exp_str}") if line.startswith(f"### {user} ") else line for line in lines]
    write_file(trojan_file, new_lines)
    
    drawit_lines = read_file(drawit_file)
    new_drawit_lines = []
    for line in drawit_lines:
        if line.startswith(f"###ws {user} {exp}"):
            new_line = line.replace(f"###ws {user} {exp}", f"###ws {user} {new_exp_str}")
        elif line.startswith(f"###grpc {user} {exp}"):
            new_line = line.replace(f"###grpc {user} {exp}", f"###grpc {user} {new_exp_str}")
        else:
            new_line = line
        new_drawit_lines.append(new_line)
    
    write_file(drawit_file, new_drawit_lines)
    
    return f"User {user} trojan extended to {new_exp_str}"
    
@app.route("/renewvless")
def renewvless():
    masaaktif = int(request.args.get("exp"))
    user = request.args.get("user")
    vless_file = '/etc/.vless'
    sketsa_file = '/etc/default/syncron/sketsa/sketsa.json'
    lines = read_file(vless_file)
    user_line = next((line for line in lines if line.startswith(f"### {user} ")), None)
    if not user_line:
        return "User not found"
    exp = user_line.split()[2]
    now = datetime.now().strftime("%Y-%m-%d")
    current_exp_date = datetime.strptime(exp, "%Y-%m-%d")
    current_date = datetime.strptime(now, "%Y-%m-%d")
    delta_days = (current_exp_date - current_date).days
    new_exp_date = current_date + timedelta(days=delta_days + masaaktif)
    new_exp_str = new_exp_date.strftime("%Y-%m-%d")
    new_lines = [line.replace(f"### {user} {exp}", f"### {user} {new_exp_str}") if line.startswith(f"### {user} ") else line for line in lines]
    write_file(vless_file, new_lines)
    
    sketsa_lines = read_file(sketsa_file)
    new_sketsa_lines = []
    for line in sketsa_lines:
        if line.startswith(f"###ws {user} {exp}"):
            new_line = line.replace(f"###ws {user} {exp}", f"###ws {user} {new_exp_str}")
        elif line.startswith(f"###grpc {user} {exp}"):
            new_line = line.replace(f"###grpc {user} {exp}", f"###grpc {user} {new_exp_str}")
        else:
            new_line = line
        new_sketsa_lines.append(new_line)
    
    write_file(sketsa_file, new_sketsa_lines)
    
    return f"User {user} vless extended to {new_exp_str}"
    
@app.route("/create-vless")
def create_vless():
    user = request.args.get("user")
    quota = request.args.get("quota")
    limit_ip = request.args.get("limitip")
    exp = request.args.get("exp")

    logging.debug(f"Received parameters: user={user}, quota={quota}, limit_ip={limit_ip}, exp={exp}")

    if not all([user, quota, limit_ip, exp]):
        logging.error("Missing parameters")
        return "Missing parameters", 400

    exp = int(exp)
    uid = uuid.uuid4()

    grep_process = subprocess.Popen(['grep', '-w', user, '/etc/default/syncron/sketsa/sketsa.json'], stdout=subprocess.PIPE)
    grep_output, _ = grep_process.communicate()
    if grep_output:
        logging.error(f"User {user} already exists")
        return "User already exists", 400

    today = datetime.today()
    later = today + timedelta(days=exp)
    bytes_quota = int(quota) * (1024 ** 3)  # 1 GB = 1024^3 bytes

    try:
        sed_command = r'sed -i "/#vless$/a\###ws {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/sketsa/sketsa.json")
        logging.debug(f"Running command: {sed_command}")
        subprocess.run(sed_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sed_command1 = r'sed -i "/#grpcvless$/a\###grpc {} {} {}\\n}},{{\"id\": \"{}\",\"alterId\": 0,\"email\": \"{}\"" {}'.format(
            user, later.strftime('%Y-%m-%d'), str(uid), str(uid), user, "/etc/default/syncron/sketsa/sketsa.json")
        logging.debug(f"Running command: {sed_command1}")
        subprocess.run(sed_command1, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        subprocess.run(f'echo "{limit_ip}" > "/etc/rycle/vless/limit/{user}"', shell=True, check=True)
        subprocess.run(f'echo "{bytes_quota}" > /etc/potatonc/limit/vless/{user}', shell=True, check=True)

        with open('/etc/.vless', 'a') as vless_file:
            vless_file.write(f"### {user} {later.strftime('%Y-%m-%d')} {uid}\n")

        subprocess.run(["systemctl", "restart", "sketsa"], check=True)

        vless_link = f"vless://{uid}@bugkamu.com:443?path=%2Fvless&security=tls&host={domain}&type=ws&sni={domain}#{user}"
        vless_link1 = f"vless://{uid}@{domain}:443?mode=gun&security=tls&type=grpc&serviceName=vless&sni=bug.com#{user}"
        vless_link2 = f"vless://{uid}@bugkamu.com:80?path=%2Fvless&security=none&host={domain}&type=ws&sni={domain}#{user}"

        return {
            "vless_link": vless_link,
            "vless_link1": vless_link1,
            "vless_link2": vless_link2
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e}")
        return str(e), 500   
                
@app.route("/delete/<protocol>/<user>", methods=["DELETE"])
def delete_user(protocol, user):
    if protocol not in ["vmess", "trojan", "vless"]:
        logging.error(f"Invalid protocol: {protocol}")
        return "Invalid protocol", 400

    json_file = {
        "vmess": "/etc/default/syncron/paradis/paradis.json",
        "trojan": "/etc/default/syncron/drawit/drawit.json",
        "vless": "/etc/default/syncron/sketsa/sketsa.json"
    }

    limit_path = {
        "vmess": "/etc/rycle/vmess/limit/",
        "trojan": "/etc/rycle/trojan/limit/",
        "vless": "/etc/rycle/vless/limit/"
    }

    quota_path = {
        "vmess": "/etc/potatonc/limit/vmess/",
        "trojan": "/etc/potatonc/limit/trojan/",
        "vless": "/etc/potatonc/limit/vless/"
    }

    log_file = {
        "vmess": "/etc/.vmess",
        "trojan": "/etc/.trojan",
        "vless": "/etc/.vless"
    }

    service = {
        "vmess": "paradis",
        "trojan": "drawit",
        "vless": "sketsa"
    }

    # Cek apakah user ada di file JSON
    grep_process = subprocess.Popen(['grep', '-w', user, json_file[protocol]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    grep_output, grep_error = grep_process.communicate()

    if grep_process.returncode != 0:
        logging.error(f"Grep error: {grep_error.decode('utf-8')}")
        return f"User does not exist in {protocol}", 400
    
    logging.info(f"Grep output: {grep_output.decode('utf-8')}")

    try:
        # Hapus user dari file log
        sed_log_command = f'sed -i "/### {user} /d" {log_file[protocol]}'
        result_log = subprocess.run(sed_log_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result_log.returncode != 0:
            logging.error(f"sed log command error: {result_log.stderr.decode('utf-8')}")
        else:
            logging.info(f"sed log command output: {result_log.stdout.decode('utf-8')}")

        # Hapus blok JSON terkait user
        sed_json_command = f'sed -i "/^###ws {user} /,/^}}/d" {json_file[protocol]}'
        sed_json_command1 = f'sed -i "/^###grpc {user} /,/^}}/d" {json_file[protocol]}'
        subprocess.run(sed_json_command1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result_json = subprocess.run(sed_json_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result_json.returncode != 0:
            logging.error(f"sed json command error: {result_json.stderr.decode('utf-8')}")
        else:
            logging.info(f"sed json command output: {result_json.stdout.decode('utf-8')}")

        # Hapus file limit dan quota
        rm_limit_result = subprocess.run(f'rm -f {limit_path[protocol]}{user}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if rm_limit_result.returncode != 0:
            logging.error(f"rm limit command error: {rm_limit_result.stderr.decode('utf-8')}")
        else:
            logging.info(f"rm limit command output: {rm_limit_result.stdout.decode('utf-8')}")

        rm_quota_result = subprocess.run(f'rm -f {quota_path[protocol]}{user}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if rm_quota_result.returncode != 0:
            logging.error(f"rm quota command error: {rm_quota_result.stderr.decode('utf-8')}")
        else:
            logging.info(f"rm quota command output: {rm_quota_result.stdout.decode('utf-8')}")

        # Restart service
        restart_result = subprocess.run(["systemctl", "restart", service[protocol]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if restart_result.returncode != 0:
            logging.error(f"systemctl restart error: {restart_result.stderr.decode('utf-8')}")
        else:
            logging.info(f"systemctl restart output: {restart_result.stdout.decode('utf-8')}")

        return f"User {user} deleted successfully from {protocol}", 200

    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {str(e)}")
        return f"Error executing command: {str(e)}", 500


@app.route("/trialssh")
def trial_ssh():
    # Generate random username and password
    username = "trialX-" + str(random.randint(10, 1000))
    password = "semok-" + str(random.randint(10, 1000))
    exp_days = "1"
    today = datetime.now()
    later = today + timedelta(days=int(exp_days))  # Correcting timedelta usage
    exp_timestamp = int(later.timestamp())  # Expiry timestamp for logging

    try:
        # Create the user with expiration date
        subprocess.check_output(f'useradd -e `date -d "{exp_days} days" +"%Y-%m-%d"` -s /bin/false -M {username}', shell=True)

        # Set the user's password
        subprocess.check_output(f'usermod --password $(echo {password} | openssl passwd -1 -stdin) {username}', shell=True)

        # Log the user's details
        subprocess.check_output(f'echo "### {username} {password} `date -d "{exp_days} days" +"%Y-%m-%d"` {exp_timestamp}" >> /etc/.trialssh', shell=True)

    except Exception as e:
        return "error"

    # Return the username and password
    return {"username": username, "password": password, "expiry": later.strftime("%Y-%m-%d %H:%M:%S")}

@app.route("/adduser/exp")
def add_user_exp():
    # Get query parameters
    username = request.args.get("user")
    password = request.args.get("password")
    exp_days = request.args.get("exp")
    limit_ip = request.args.get("limitip")

    try:
        # Create the user with expiration date
        subprocess.check_output(f'useradd -e `date -d "{exp_days} days" +"%Y-%m-%d"` -s /bin/false -M {username}', shell=True)

        # Set the user's password
        subprocess.check_output(f'usermod --password $(echo {password} | openssl passwd -1 -stdin) {username}', shell=True)

        # Log the user's details
        subprocess.check_output(f'echo "### {username} `date -d "{exp_days} days" +"%Y-%m-%d"` {password} {limit_ip}" >> /etc/.sshdb', shell=True)

    except Exception as e:
        return "error"

    return "success"

@app.route("/renewssh")
def renew_ssh():
    # Get query parameters
    username = request.args.get("user")
    add_days = request.args.get("exp")

    try:
        # Dapatkan tanggal kadaluarsa baru berdasarkan jumlah hari yang ditambahkan
        new_exp_date = subprocess.check_output(f'date -d "{add_days} days" +"%Y-%m-%d"', shell=True).decode().strip()

        # Update the expiration date of the user
        subprocess.check_output(f'chage -E {new_exp_date} {username}', shell=True)

        # Gunakan sed untuk mengganti tanggal kadaluarsa pada entri pengguna di /etc/.sshdb
        # Format dari entri log: "### username expiration_date password limit_ip"
        subprocess.check_output(f'sed -i "s/^### {username} [0-9-]*/### {username} {new_exp_date}/" /etc/.sshdb', shell=True)

    except Exception as e:
        return f"error: {str(e)}"

    return f"User {username} ssh extended to {new_exp_date}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 6000
    app.run(host="0.0.0.0", port=port)
