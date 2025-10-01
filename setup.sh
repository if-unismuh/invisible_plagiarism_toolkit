#!/bin/bash
# 
# Invisible Plagiarism Toolkit - Setup Script
# Professional Document Manipulation System
#

set -e

echo "🔮 INVISIBLE PLAGIARISM TOOLKIT SETUP"
echo "======================================"

# Check Python version
echo "📋 Checking Python version..."
python3 --version || { echo "❌ Python 3.8+ required"; exit 1; }

# Install system dependencies
echo "📦 Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y ocrmypdf tesseract-ocr tesseract-ocr-ind
elif command -v brew &> /dev/null; then
    brew install ocrmypdf tesseract tesseract-lang
else
    echo "⚠️  Please install ocrmypdf and tesseract manually"
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# Create workspace structure
echo "📁 Setting up workspace..."
mkdir -p workspace/input/{original,turnitin}
mkdir -p workspace/output/{processed,analysis,reports}
mkdir -p workspace/temp

# Make main.py executable
chmod +x main.py

# Test installation
echo "🧪 Testing installation..."
PYTHONPATH=./src python main.py --check-deps

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Quick Start:"
echo "1. Place original DOCX in: workspace/input/original/"
echo "2. Place Turnitin PDF in: workspace/input/turnitin/"
echo "3. Run: PYTHONPATH=./src python main.py --mode balanced"
echo ""
echo "📚 Documentation: README.md"
echo "🆘 Support: GitHub Issues"
