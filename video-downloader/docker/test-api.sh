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
FAILURES=0

# Test 1: Health check
echo "Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/health" \
  -H "Authorization: Bearer $API_KEY")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
    FAILURES=$((FAILURES + 1))
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
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Test 3: Submit download (requires API key)
echo "Test 3: Submit Download Job"
response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/download" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    "title": "Test Video",
    "referer": "https://test-streams.mux.dev"
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
    FAILURES=$((FAILURES + 1))
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
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Test 5: List jobs with filters (status/limit)
echo "Test 5: List Jobs (Filters)"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/jobs?status=pending&limit=1" \
  -H "Authorization: Bearer $API_KEY")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
    echo "Response: $body"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Test 6: Get job details (if we have a job ID)
if [ -n "$JOB_ID" ]; then
    echo "Test 6: Get Job Details"
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
        FAILURES=$((FAILURES + 1))
    fi
    echo ""
fi

# Test 7: Cancel job (DELETE) and verify status (if we have a job ID)
if [ -n "$JOB_ID" ]; then
    echo "Test 7: Cancel Job"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL/api/jobs/$JOB_ID" \
      -H "Authorization: Bearer $API_KEY")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Status: $http_code"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAIL${NC} - Status: $http_code"
        echo "Response: $body"
        FAILURES=$((FAILURES + 1))
    fi
    echo ""

    echo "Test 8: Get Job Details (After Cancel)"
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
        FAILURES=$((FAILURES + 1))
    fi
    echo ""
fi

# Test 9: System status
echo "Test 9: System Status"
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
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "========================================="
echo "Tests complete!"
if [ "$FAILURES" -gt 0 ]; then
    echo -e "${RED}FAILED${NC} - $FAILURES test(s) failed"
    exit 1
fi
echo -e "${GREEN}PASSED${NC} - All tests passed"
echo "========================================="
echo ""
echo "Usage:"
echo "  API_KEY=your-key ./test-api.sh"
echo "  API_URL=http://192.168.1.100:52052 API_KEY=your-key ./test-api.sh"
echo ""

