#!/bin/bash
set -e

echo "=== Frontend Build Script ==="
echo "PWD: $(pwd)"
echo ""

cd frontend

echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"
echo ""

echo "Step 1: Install dependencies..."
npm install --legacy-peer-deps --no-audit 2>&1 | tail -20

echo ""
echo "Step 2: Build with Vite..."
npm run build 2>&1 | tail -50

echo ""
echo "Step 3: Verify build output..."
if [ -d "dist" ]; then
    echo "✅ dist/ directory created"
    ls -lah dist/ | head -20
    
    if [ -f "dist/index.html" ]; then
        echo "✅ index.html exists"
    else
        echo "⚠️  index.html not found in dist/"
    fi
else
    echo "❌ dist/ directory NOT created"
    echo "Listing frontend directory:"
    ls -lah
fi

cd ..
echo ""
echo "=== Build Complete ==="
