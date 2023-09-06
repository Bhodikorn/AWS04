#!/bin/bash
USER=$(whoami)

# Get Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
# Set rootless
dockerd-rootless-setuptool.sh install
# Export PATH
export PATH=/usr/bin:$PATH
echo "export PATH=/usr/bin:\$PATH" >> /home/$USER/.bashrc