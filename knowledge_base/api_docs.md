# SenAI API Documentation

## API Versions

- Current stable version: v2
- Legacy version: v1 (deprecated, EOL: December 31, 2025)
- v1 users must migrate to v2 before EOL date

## Rate Limits by Plan

- Starter: 1,000 requests/month, 10 requests/minute
- Standard: 10,000 requests/month, 60 requests/minute
- Professional: 100,000 requests/month, 300 requests/minute
- Enterprise: Unlimited requests, custom rate limits

## v2 Breaking Changes from v1

- Authentication: API keys now use Bearer token format
- Response format: All responses now wrapped in {data: {}, meta: {}} envelope
- Pagination: Changed from page/limit to cursor-based pagination
- Webhooks: New signature verification required (HMAC-SHA256)
- Removed endpoints: /v1/legacy/_, /v1/old-format/_

## Required Headers (v2)

- Authorization: Bearer {api_key}
- Content-Type: application/json
- X-API-Version: 2.0
- X-Request-ID: (optional) for idempotency

## Webhook Configuration

- Events: email.received, email.replied, ticket.created, ticket.resolved
- Retry policy: 3 attempts with exponential backoff
- Timeout: 30 seconds per webhook call
- Signature header: X-SenAI-Signature (HMAC-SHA256)

## Common Error Codes

- 429: Rate limit exceeded, retry after X seconds
- 401: Invalid or expired API key
- 403: Feature not available on current plan
- 422: Validation error in request body
