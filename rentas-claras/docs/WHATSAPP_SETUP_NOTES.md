# WhatsApp Business API Setup Notes

## Dad's Business Account (Rentas Claras)

### 🔗 Quick Links

| Resource | Link |
|----------|------|
| **Security Center (Check Verification Status)** | https://business.facebook.com/latest/settings/security_center/?nav_ref=bm_settings_redirect_migration&bm_redirect_migration=true&business_id=923696060596735 |
| **Business Manager ID** | `923696060596735` |

---

## Coexistence Setup Checklist

Before enabling WhatsApp auto messages via Coexistence:

- [ ] Phone number is WhatsApp Business App (not consumer)
- [ ] Country is eligible (Mexico ✅)
- [ ] App has required permissions:
  - `business_management`
  - `whatsapp_business_management`
  - `whatsapp_business_messaging`
- [ ] Business Verification status: Check at Security Center link above

---

## Useful External Links

| Resource | Link |
|----------|------|
| Developer Docs (Coexistence) | https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users |
| Help Center | https://faq.whatsapp.com/8122483904494954/ |
| Direct Support | https://business.facebook.com/direct-support/ |

---

## Environment Variables Needed

```bash
WHATSAPP_ACCESS_TOKEN=<your_token>
WHATSAPP_PHONE_NUMBER_ID=<phone_number_id>
WHATSAPP_BUSINESS_ACCOUNT_ID=<waba_id>
WHATSAPP_TEST_PHONE=<test_phone_for_debugging>
```

---

## Notes

- Last updated: 2026-01-01
- Business Manager belongs to dad's account for Rentas Claras
