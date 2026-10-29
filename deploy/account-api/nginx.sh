set -e
T=$(date +%Y%m%d%H%M%S)
cp /etc/nginx/sites-available/openduolaimi /home/xiaofei/ngx-duo.bak-acct-$T
python3 /tmp/odapi/patch_nginx.py
if nginx -t; then systemctl reload nginx; echo RELOADED; else cp /home/xiaofei/ngx-duo.bak-acct-$T /etc/nginx/sites-available/openduolaimi; echo ROLLED_BACK; fi
echo backup=/home/xiaofei/ngx-duo.bak-acct-$T
