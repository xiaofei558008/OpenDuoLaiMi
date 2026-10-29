#!/bin/sh
# daily pg_dump of opendoremi, keep 14 days (local only)
set -e
D=/var/backups/opendoremi
mkdir -p $D
F=$D/opendoremi-$(date +%Y%m%d-%H%M%S).sql.gz
sudo -u postgres pg_dump opendoremi | gzip -9 > $F.tmp && mv $F.tmp $F
chmod 600 $F
find $D -name 'opendoremi-*.sql.gz' -mtime +13 -delete
