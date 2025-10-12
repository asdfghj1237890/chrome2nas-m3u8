#!/bin/bash
# Test script for API endpoints

API_URL="${API_URL:-http://localhost:52052}"
API_KEY="${API_KEY:-change-this-key}"

echo "========================================="
echo "API Test Script"
echo "========================================="
echo "API URL: $API_URL"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root Endpoint"
response=$(curl -s -w "\n%{http_code}" "$API_URL/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
fi
echo ""

# Test 3: Submit download (requires API key)
echo "Test 3: Submit Download Job"
response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/download" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test.example.com/test.m3u8",
    "title": "Test Video",
    "referer": "https://test.example.com"
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
    
    # Extract job ID for next test
    JOB_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "Job ID: $JOB_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
    echo "Note: Make sure API_KEY is set correctly"
fi
echo ""

# Test 4: List jobs
echo "Test 4: List Jobs"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/jobs" \
  -H "Authorization: Bearer $API_KEY")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
fi
echo ""

# Test 5: Get job details (if we have a job ID)
if [ -n "$JOB_ID" ]; then
    echo "Test 5: Get Job Details"
    response=$(curl -s -w "\n%{http_code}" "$API_URL/api/jobs/$JOB_ID" \
      -H "Authorization: Bearer $API_KEY")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
        echo "Response: $body"
    fi
    echo ""
fi

# Test 6: System status
echo "Test 6: System Status"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/status" \
  -H "Authorization: Bearer $API_KEY")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
fi
echo ""

echo "========================================="
echo "Tests complete!"
echo "========================================="
echo ""
echo "Usage:"
echo "  API_KEY=your-key ./test-api.sh"
echo "  API_URL=http://192.168.1.100:52052 API_KEY=your-key ./test-api.sh"
echo ""

