cd /var/www/music-data/songs && find . -type f ! -name "*.tmp" -printf "%s %p\n" > ~/alilist.txt; wc -l ~/alilist.txt
