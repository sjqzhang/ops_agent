path=/tmp/easyops/easyops/install
if [ -d ${path} ]; then
    find ${path}/* -maxdepth 1 -prune -type d -mtime +3 | xargs rm -rf
fi

path=/tmp/easyops/easyops/update
if [ -d ${path} ]; then
    find ${path}/* -maxdepth 1 -prune -type d -mtime +3 | xargs rm -rf
fi
