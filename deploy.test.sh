#!/bin/bash
# Deploy script to deploy test LCP on http://lcp.test.linguistik.uzh.ch/
set -e

PROJ_DIR=/opt
DATE=`date +"%Y-%m-%d %H:%M:%S"`

APP_DIR=$PROJ_DIR/lcp.test
APP_NAME="lcp"
YARN_ARGS="build:lcp"

# 1. Log deploy (Start)
printf "%7s: %s\n" "$DATE" "$APP_NAME" >> $APP_DIR/deploy.log

# 2. Go to folder and fetch git
cd $APP_DIR/app
git fetch --tags

# 3. Checkout to tag/pull master branch
# git checkout $TAG
git pull

# 4. Install new FE packages
cd $APP_DIR/app/frontend
yarn install

# 5. Build frontend
yarn $YARN_ARGS

# 6. Install/upgrade BE packages
. $APP_DIR/env/bin/activate
cd $APP_DIR/app
pip install -U -r requirements.txt

# 7. Install abstract-query
cd abstract-query
git pull
python setup.py develop

# 8. Restart BE
sudo redis-cli flushall
sudo systemctl restart lcp.worker.test@1.service
sudo systemctl restart lcp.worker.test@2.service
sudo systemctl restart lcp.worker.test@3.service
sudo systemctl restart lcp.web.test.service

# 9. Log deploy (Finish)
DATE=`date +"%Y-%m-%d %H:%M:%S"`
printf "%7s: Done\n" "$DATE" >> $APP_DIR/deploy.log
