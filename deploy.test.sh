#!/bin/bash
set -e

PROJ_DIR=/opt
DATE=`date +"%Y-%m-%d %H:%M:%S"`

APP_DIR=$PROJ_DIR/lcp.test
APP_NAME="lcp"
YARN_ARGS="build"

# 1. Log deploy
printf "%7s: %s\n" "$DATE" "$APP_NAME" >> $APP_DIR/deploy.log

# 2. Go to folder and fetch git
cd $APP_DIR/app
git fetch --tags

# 3. Checkout to tag
# git checkout $TAG
git pull

# 4. Install new FE packages
cd $APP_DIR/app/frontend
yarn install

# 5. Build frontend
export NODE_ENV=staging
yarn $YARN_ARGS
rm -rf $APP_DIR/app/frontend/dist_web
cp -rf $APP_DIR/app/frontend/dist $APP_DIR/app/frontend/dist_web

# 6. Install new BE packages
. $APP_DIR/env/bin/activate
cd $APP_DIR/app
if test -f "requirements.txt"
then
    pip install -U -r requirements.txt
else
    python -m pip install .
fi

# 7. Restart BE
#sudo redis-cli flushall
sudo systemctl restart lcp.worker.test@1.service
sudo systemctl restart lcp.worker.test@2.service
sudo systemctl restart lcp.worker.test@3.service
sudo systemctl restart lcp.web.test.service

# 8. Log deploy
DATE=`date +"%Y-%m-%d %H:%M:%S"`
printf "%7s: Done\n" "$DATE" >> $APP_DIR/deploy.log
