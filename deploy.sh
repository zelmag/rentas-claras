#!/bin/bash

# VueloDigno Deployment Script
# This script automates deployment to Vercel

set -e  # Exit on any error

echo "🚀 VueloDigno Deployment Script"
echo "================================"
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found!"
    echo ""
    echo "Please install it first:"
    echo "  npm install -g vercel"
    echo ""
    echo "If npm is not installed, download Node.js from:"
    echo "  https://nodejs.org/"
    exit 1
fi

echo "✓ Vercel CLI found"
echo ""

# Check if logged in to Vercel
echo "Checking Vercel login status..."
if ! vercel whoami &> /dev/null; then
    echo "Please log in to Vercel..."
    vercel login
else
    echo "✓ Already logged in to Vercel"
fi

echo ""
echo "📝 Checking environment variables..."

# Check if environment variables are set locally
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with:"
    echo "  RESEND_API_KEY=your_key_here"
    echo "  FROM_EMAIL=reclamos@vuelodigno.com"
    exit 1
fi

echo "✓ .env file found"
echo ""

# Deploy to production
echo "🚀 Deploying to Vercel production..."
echo ""
vercel --prod

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Vercel (if not already set):"
echo "   vercel env add RESEND_API_KEY"
echo "   vercel env add FROM_EMAIL"
echo ""
echo "2. Verify domain is linked:"
echo "   vercel domains ls"
echo ""
echo "3. Add domain if needed:"
echo "   vercel domains add vuelodigno.com"
echo ""
echo "4. Test your site:"
echo "   https://vuelodigno.com"
echo ""
echo "View deployment logs:"
echo "   vercel logs"
echo ""
