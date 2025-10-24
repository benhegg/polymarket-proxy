#!/bin/bash
# Quick setup script for Railway deployment
# Run this from your LOCAL machine after cloning the repo

echo "🚂 Railway Deployment Helper"
echo "=============================="
echo ""

# Check if in correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Not in python-backend directory"
    echo "Please run: cd python-backend"
    exit 1
fi

echo "✅ In correct directory"
echo ""

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

echo "🔐 Logging into Railway..."
railway login

echo "🚀 Initializing Railway project..."
railway init

echo "📤 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Get your URL:"
railway domain

echo ""
echo "📋 Next steps:"
echo "1. Copy the Railway URL above"
echo "2. Go to your Vercel site"
echo "3. Click '⚙️ Config' button"
echo "4. Paste the Railway URL"
echo "5. Click 'Save & Reload'"
echo ""
echo "🐋 Done! Your whale tracker is live!"
