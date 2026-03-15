#!/bin/bash

echo "reloading bob from github..."
echo "stopping bob9k service..."
sudo service bob9k stop
sleep 1

echo "pulling from github..."
git pull
sleep 1

echo "starting bob9k service..."
sudo service bob9k start

