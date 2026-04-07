import os
import ftplib

# Parse .env securely
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env_vars[k] = v.strip('"\'')

host = env_vars.get("FTP_HOST")
user = env_vars.get("FTP_USER")
passwd = env_vars.get("FTP_PASS")

def create_remote_dir(ftp, dir_path):
    """Recursively create directories on FTP."""
    if dir_path != '':
        try:
            ftp.cwd(dir_path)
        except ftplib.error_perm:
            create_remote_dir(ftp, os.path.dirname(dir_path))
            ftp.mkd(dir_path)
            ftp.cwd(dir_path)

print(f"Connecting to FTP server {host} as {user}...")
try:
    ftp = ftplib.FTP(host)
    ftp.login(user, passwd)
    print("Login successful. Uploading static files...")
    
    local_dir = "public_website"
    for root, dirs, files in os.walk(local_dir):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, local_dir)
            remote_path = rel_path.replace("\\", "/")
            
            # Go to root
            ftp.cwd('/')
            
            # Create remote directory structure if needed
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                create_remote_dir(ftp, remote_dir)
                
            # Upload file
            ftp.cwd('/')
            if remote_dir:
                ftp.cwd(remote_dir)
                
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {os.path.basename(remote_path)}", f)
                print(f"  [+] Uploaded: {remote_path}")
                
    ftp.quit()
    print("Static website upload complete.")
    
except Exception as e:
    print(f"FTP Error: {e}")
