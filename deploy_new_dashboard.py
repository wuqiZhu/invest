import paramiko
import sys
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting server...")
    ssh.connect('188.166.249.182', username='root', password='13979831637zhu', timeout=15)
    print("Connected successfully!")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

print("\nUploading dashboard.html...")
sftp = ssh.open_sftp()
with open('scripts/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()
with sftp.open('/root/projects/invest/scripts/dashboard.html', 'w') as f:
    f.write(content)
sftp.close()
print("File uploaded!")

print("\nRestarting container...")
stdin, stdout, stderr = ssh.exec_command('cd /root/projects && docker compose restart invest-backend')
print(stdout.read().decode())
print(stderr.read().decode())

print("\nWaiting for service...")
time.sleep(3)

print("\nDeployment complete!")
print("\nVisit: http://188.166.249.182:5000/")
print("\nNew features:")
print("  - Modern UI design (inspired by Ghostfolio)")
print("  - Sidebar navigation")
print("  - ECharts: Trend + Allocation")
print("  - Table view for holdings")
print("  - Better visual style")

ssh.close()
