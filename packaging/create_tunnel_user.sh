#!/bin/bash
USERNAME=$1
if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username>"
    exit 1
fi

PASSWORD=$(openssl rand -base64 16 | tr -dc 'A-Za-z0-9' | head -c 16)

sudo useradd -m -s /usr/sbin/nologin $USERNAME
echo "$USERNAME:$PASSWORD" | sudo chpasswd
# 确保sshd允许端口转发
sudo sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config
# 添加用户限制
if ! grep -q "Match User $USERNAME" /etc/ssh/sshd_config; then
    cat >> /etc/ssh/sshd_config <<EOF
Match User $USERNAME
    AllowTcpForwarding yes
    X11Forwarding no
    ForceCommand /bin/false
EOF
fi
sudo systemctl restart sshd
echo "隧道账号已创建: $USERNAME"
echo "密码: $PASSWORD"
echo "用户连接命令: ssh -L <本地端口>:<目标>:<目标端口> $USERNAME@<服务器IP>"
