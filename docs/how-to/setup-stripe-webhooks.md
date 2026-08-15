# Stripe Webhooks Setup Guide

**Project:** QA-FRAMEWORK SaaS MVP
**Last Updated:** 2026-03-05 21:00 UTC
**Time Required:** 10 minutes

---

## 🎯 Overview

This guide explains how to configure Stripe webhooks to enable real-time payment and subscription notifications for the QA-FRAMEWORK application.

---

## ✅ Prerequisites

- [x] Stripe account created (already configured ✅)
- [x] Backend deployed at `qa-framework-backend.railway.app`
- [x] Stripe API key configured in environment
- [x] Webhook endpoint implemented (`/api/v1/billing/webhook`)

---

## 📋 Step-by-Step Setup

### Step 1: Access Stripe Dashboard

1. Go to https://dashboard.stripe.com/
2. Log in to your Stripe account
3. Ensure you're in **Live mode** (toggle in top right)

**Time:** 1 minute

---

### Step 2: Navigate to Webhooks

1. Click on **Developers** in the left sidebar
2. Click on **Webhooks**
3. Click **Add endpoint** button

**Time:** 1 minute

---

### Step 3: Configure Webhook Endpoint

**Endpoint URL:**
```
https://qa-framework-backend.railway.app/api/v1/billing/webhook
```

**Events to listen to (select "Select events"):**

#### Subscription Events
- [ ] `customer.subscription.created`
- [ ] `customer.subscription.updated`
- [ ] `customer.subscription.deleted`

#### Payment Events
- [ ] `invoice.payment_succeeded`
- [ ] `invoice.payment_failed`
- [ ] `payment_intent.succeeded`
- [ ] `payment_intent.payment_failed`

#### Customer Events
- [ ] `customer.created`
- [ ] `customer.updated`
- [ ] `customer.deleted`

**Recommended:** Select all subscription and payment events (8 events total)

**Time:** 3 minutes

---

### Step 4: Get Webhook Signing Secret

1. After creating the webhook, click on it to view details
2. In the **Signing secret** section, click **Reveal**
3. Copy the signing secret (starts with `whsec_...`)
4. **IMPORTANT:** Save this secret securely

**Time:** 1 minute

---

### Step 5: Configure Environment Variable

Add the webhook signing secret to your Railway environment:

1. Go to https://railway.app/
2. Navigate to your QA-FRAMEWORK backend project
3. Click on **Variables** tab
4. Add new variable:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_YOUR_SIGNING_SECRET_HERE
   ```
5. Railway will automatically redeploy with the new variable

**Time:** 2 minutes

---

### Step 6: Verify Webhook Configuration

#### Test with Stripe CLI (Optional but Recommended)

1. Install Stripe CLI:
   ```bash
   # macOS
   brew install stripe/stripe-cli/stripe
   
   # Linux
   wget https://github.com/stripe/stripe-cli/releases/download/v1.19.4/stripe_1.19.4_linux_x86_64.tar.gz
   tar -xvf stripe_1.19.4_linux_x86_64.tar.gz
   sudo mv stripe /usr/local/bin/
   ```

2. Login to Stripe:
   ```bash
   stripe login
   ```

3. Test webhook locally:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/billing/webhook
   ```

4. In another terminal, trigger test event:
   ```bash
   stripe trigger customer.subscription.created
   ```

**Time:** 2 minutes

---

## 🔍 Verification Checklist

After completing setup, verify:

- [ ] Webhook endpoint appears in Stripe dashboard
- [ ] Signing secret is configured in Railway
- [ ] Backend has redeployed with new environment variable
- [ ] Test webhook from Stripe dashboard succeeds (200 OK)
- [ ] Logs show webhook received and processed

---

## 🧪 Testing Webhooks

### Manual Test from Stripe Dashboard

1. Go to **Developers** → **Webhooks**
2. Click on your webhook endpoint
3. Click **Send test webhook** button
4. Select event type: `customer.subscription.created`
5. Click **Send test webhook**
6. Verify response shows **200 OK**
7. Check backend logs for webhook processing

---

## 📊 Monitored Events

The application handles the following Stripe events:

| Event | Action | Priority |
|-------|--------|----------|
| `customer.subscription.created` | Activate subscription features | HIGH |
| `customer.subscription.updated` | Update plan/limits | HIGH |
| `customer.subscription.deleted` | Downgrade to free tier | HIGH |
| `invoice.payment_succeeded` | Confirm payment, extend access | HIGH |
| `invoice.payment_failed` | Send payment failed notification | MEDIUM |
| `payment_intent.succeeded` | Log successful payment | LOW |
| `payment_intent.payment_failed` | Log failed payment attempt | LOW |
| `customer.created` | Link Stripe customer to user | LOW |
| `customer.updated` | Update customer metadata | LOW |
| `customer.deleted` | Handle account deletion | MEDIUM |

---

## 🚨 Troubleshooting

### Webhook Returns 400 Bad Request

**Cause:** Invalid signature or payload
**Solution:** Verify `STRIPE_WEBHOOK_SECRET` matches the signing secret from Stripe dashboard

### Webhook Returns 500 Internal Server Error

**Cause:** Application error processing webhook
**Solution:** Check backend logs for detailed error message

### Webhook Not Received

**Cause:** Incorrect endpoint URL or firewall blocking
**Solution:** 
1. Verify URL is exactly `https://qa-framework-backend.railway.app/api/v1/billing/webhook`
2. Ensure Railway service is running
3. Check Railway logs for incoming requests

### Signature Verification Failed

**Cause:** Webhook secret mismatch or timing issue
**Solution:**
1. Regenerate signing secret in Stripe dashboard
2. Update `STRIPE_WEBHOOK_SECRET` in Railway
3. Wait for Railway to redeploy
4. Test again

---

## 🔐 Security Best Practices

1. **Always use HTTPS:** Webhooks must use HTTPS in production
2. **Verify signatures:** Never skip signature verification
3. **Idempotency:** Handle duplicate webhook events gracefully
4. **Rate limiting:** Stripe may send multiple webhooks rapidly
5. **Logging:** Log all webhook events for debugging and audit

---

## 📈 Monitoring

### Recommended Monitoring

1. **Stripe Dashboard:**
   - Check webhook success rate weekly
   - Review failed webhook attempts
   - Monitor response times

2. **Application Logs:**
   - Log all incoming webhooks
   - Log processing errors
   - Track webhook processing time

3. **Alerts:**
   - Set up alert for webhook failures > 5%
   - Alert on 500 errors from webhook endpoint
   - Monitor webhook queue backlog

---

## ✅ Completion Checklist

- [ ] Webhook endpoint created in Stripe dashboard
- [ ] All 8 required events selected
- [ ] Signing secret copied
- [ ] `STRIPE_WEBHOOK_SECRET` added to Railway
- [ ] Backend redeployed with new variable
- [ ] Test webhook sent successfully (200 OK)
- [ ] Backend logs show webhook processed
- [ ] Documentation updated

---

## 📚 Related Documentation

- [Stripe Webhooks Documentation](https://stripe.com/docs/webhooks)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)
- [Backend API Reference](../reference/api.md)
- Billing System Overview (doc pending)

---

## 🆘 Support

If you encounter issues:

1. Check Stripe dashboard for webhook delivery status
2. Review backend logs for errors
3. Verify environment variables are set correctly
4. Test with Stripe CLI for local debugging
5. Contact Stripe support for persistent issues

---

**Setup Time:** 10 minutes
**Difficulty:** Easy
**Prerequisites:** Stripe account, Backend deployed

---

*Last updated: 2026-03-05 21:00 UTC*
*Author: Alfred (OpenClaw Agent)*
