#!/bin/bash

echo "🔧 Uninstalling conflicting OpenCV version..."
pip uninstall -y opencv-python opencv-contrib-python

echo "✅ Installing clean dependencies..."
pip install -r requirements.txt