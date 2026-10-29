#!/bin/bash
# usage: sudo -S bash setup.sh  (password on stdin consumed by sudo)
set -euo pipefail
exec > /tmp/odapi-setup.log 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive
W=/tmp/odapi
apt-get update -qq
apt-get install -y -qq postgresql python3-venv python3-pip openssl
PGV=$(ls /etc/postgresql | sort -n | tail -1)
C=/etc/postgresql/$PGV/main
cat > $C/conf.d/opendoremi.conf <<'X'
listen_addresses = '127.0.0.1'
shared_buffers = 32MB
max_connections = 20
work_mem = 2MB
maintenance_work_mem = 16MB
effective_cache_size = 128MB
X
systemctl restart postgresql
# db + user
id opendoremi || useradd --system --home /opt/opendoremi-api --shell /usr/sbin/nologin opendoremi
set +x
if [ ! -f /etc/opendoremi-api.env ]; then
 DBPW=$(openssl rand -hex 24)
 sudo -u postgres psql -v ON_ERROR_STOP=1 -q -c "DO \$\$BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='opendoremi') THEN CREATE ROLE opendoremi LOGIN; END IF; END\$\$;"
 sudo -u postgres psql -q -c "ALTER ROLE opendoremi PASSWORD '$DBPW'" >/dev/null
 umask 077
 cat > /etc/opendoremi-api.env <<X
OD_DATABASE_URL=postgresql://opendoremi:$DBPW@127.0.0.1:5432/opendoremi
OD_JWT_PRIVATE_KEY=/etc/opendoremi/ed25519.pem
OD_WECHAT_ENABLED=false
X
 chmod 600 /etc/opendoremi-api.env; chown root:root /etc/opendoremi-api.env
fi
set -x
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='opendoremi'" | grep -q 1 || sudo -u postgres createdb -O opendoremi opendoremi
sudo -u postgres psql -d opendoremi -c "CREATE EXTENSION IF NOT EXISTS citext"
# key
install -d -m 750 -o root -g opendoremi /etc/opendoremi
[ -f /etc/opendoremi/ed25519.pem ] || openssl genpkey -algorithm ed25519 -out /etc/opendoremi/ed25519.pem
chown opendoremi:opendoremi /etc/opendoremi/ed25519.pem; chmod 400 /etc/opendoremi/ed25519.pem
# app
mkdir -p /opt/opendoremi-api
rm -rf /opt/opendoremi-api/server
tar xzf $W/odapi.tgz -C /opt/opendoremi-api
[ -x /opt/opendoremi-api/venv/bin/python ] || python3 -m venv /opt/opendoremi-api/venv
/opt/opendoremi-api/venv/bin/pip install -q --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r /opt/opendoremi-api/server/requirements.txt
chown -R opendoremi:opendoremi /opt/opendoremi-api
cd /opt/opendoremi-api/server
set +x
sudo -u opendoremi env $(grep -v '^#' /etc/opendoremi-api.env | xargs) ../venv/bin/alembic upgrade head
set -x
install -m 644 $W/opendoremi-api.service /etc/systemd/system/opendoremi-api.service
systemctl daemon-reload
systemctl enable opendoremi-api
systemctl restart opendoremi-api
sleep 4
curl -s 127.0.0.1:8090/healthz; echo
# backup cron
install -m 755 $W/odapi-backup.sh /usr/local/sbin/odapi-backup.sh
install -d -m 700 /var/backups/opendoremi
echo '0 4 * * * root /usr/local/sbin/odapi-backup.sh' > /etc/cron.d/opendoremi-backup
chmod 644 /etc/cron.d/opendoremi-backup
/usr/local/sbin/odapi-backup.sh
ls -la /var/backups/opendoremi
echo SETUP_DONE
