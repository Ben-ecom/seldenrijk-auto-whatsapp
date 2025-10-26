#!/usr/bin/env python3
"""
Environment Variables Checker for Railway Deployment
Checks which critical environment variables are missing or misconfigured.
"""
import os
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def check_variable(var_name: str, check_func=None) -> Tuple[bool, str]:
    """
    Check if environment variable exists and passes optional validation.

    Returns:
        (is_valid, message)
    """
    value = os.getenv(var_name)

    if not value or value.startswith("REPLACE_") or value == "your-project":
        return False, "Missing or placeholder value"

    if check_func:
        try:
            check_func(value)
        except ValueError as e:
            return False, str(e)

    return True, "✓ Configured"

def check_url(value: str):
    """Validate URL format."""
    if not value.startswith(("http://", "https://")):
        raise ValueError("Must start with http:// or https://")

def check_twilio_sid(value: str):
    """Validate Twilio Account SID format."""
    if not value.startswith("AC") or len(value) != 34:
        raise ValueError("Invalid Twilio SID format (should start with AC and be 34 chars)")

def check_twilio_number(value: str):
    """Validate Twilio WhatsApp number format."""
    if not value.startswith("whatsapp:+"):
        raise ValueError("Should be in format: whatsapp:+31XXXXXXXXX")

def main():
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}  Railway Environment Variables Health Check{RESET}")
    print(f"{BOLD}{BLUE}  Seldenrijk Auto WhatsApp AI Platform{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    # Define critical variables
    critical_vars = {
        "🤖 AI & Database": [
            ("ANTHROPIC_API_KEY", None),
            ("SUPABASE_URL", check_url),
            ("SUPABASE_KEY", None),
        ],
        "📱 WhatsApp (Twilio)": [
            ("TWILIO_ACCOUNT_SID", check_twilio_sid),
            ("TWILIO_AUTH_TOKEN", None),
            ("TWILIO_WHATSAPP_NUMBER", check_twilio_number),
            ("TWILIO_WEBHOOK_URL", check_url),
        ],
        "💬 Chatwoot": [
            ("CHATWOOT_BASE_URL", check_url),
            ("CHATWOOT_API_TOKEN", None),
            ("CHATWOOT_ACCOUNT_ID", None),
        ],
    }

    optional_vars = {
        "📊 HubSpot CRM (Optional)": [
            ("HUBSPOT_API_KEY", None),
            ("HUBSPOT_ENABLED", None),
        ],
        "📅 Google Calendar (Optional)": [
            ("GOOGLE_SERVICE_ACCOUNT_JSON", None),
            ("GOOGLE_CALENDAR_ID", None),
            ("GOOGLE_CALENDAR_ENABLED", None),
        ],
    }

    # Check critical variables
    critical_missing = []

    print(f"{BOLD}🔴 CRITICAL Variables (Required):{RESET}\n")

    for category, vars_list in critical_vars.items():
        print(f"  {BOLD}{category}:{RESET}")
        for var_name, check_func in vars_list:
            is_valid, message = check_variable(var_name, check_func)

            if is_valid:
                print(f"    {GREEN}✓{RESET} {var_name}: {GREEN}{message}{RESET}")
            else:
                print(f"    {RED}✗{RESET} {var_name}: {RED}{message}{RESET}")
                critical_missing.append(var_name)
        print()

    # Check optional variables
    optional_missing = []

    print(f"{BOLD}🟡 OPTIONAL Variables (Enhanced Features):{RESET}\n")

    for category, vars_list in optional_vars.items():
        print(f"  {BOLD}{category}:{RESET}")
        for var_name, check_func in vars_list:
            is_valid, message = check_variable(var_name, check_func)

            if is_valid:
                print(f"    {GREEN}✓{RESET} {var_name}: {GREEN}{message}{RESET}")
            else:
                print(f"    {YELLOW}○{RESET} {var_name}: {YELLOW}{message}{RESET}")
                optional_missing.append(var_name)
        print()

    # Summary
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}📊 Summary:{RESET}\n")

    if not critical_missing:
        print(f"  {GREEN}✓ All CRITICAL variables are configured!{RESET}")
    else:
        print(f"  {RED}✗ Missing {len(critical_missing)} CRITICAL variable(s):{RESET}")
        for var in critical_missing:
            print(f"    {RED}• {var}{RESET}")

    print()

    if not optional_missing:
        print(f"  {GREEN}✓ All OPTIONAL variables are configured!{RESET}")
    else:
        print(f"  {YELLOW}○ Missing {len(optional_missing)} OPTIONAL variable(s):{RESET}")
        for var in optional_missing:
            print(f"    {YELLOW}• {var}{RESET}")

    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")

    # Recommendations
    if critical_missing:
        print(f"\n{BOLD}{RED}⚠️  ACTION REQUIRED:{RESET}")
        print(f"  Add missing CRITICAL variables in Railway:")
        print(f"  1. Go to Railway Dashboard → Your Service → Variables")
        print(f"  2. Click '+ New Variable'")
        print(f"  3. Add each missing variable")
        print(f"  4. Redeploy the service\n")
        print(f"  📖 See RAILWAY-CONFIG-GUIDE.md for detailed instructions\n")
    elif optional_missing:
        print(f"\n{BOLD}{YELLOW}💡 OPTIONAL ENHANCEMENTS:{RESET}")
        print(f"  Consider adding optional variables for:")
        if "HUBSPOT_API_KEY" in optional_missing:
            print(f"    • HubSpot CRM: Automatic lead management & deal creation")
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in optional_missing:
            print(f"    • Google Calendar: Real-time appointment scheduling")
        print(f"\n  📖 See RAILWAY-CONFIG-GUIDE.md for setup instructions\n")
    else:
        print(f"\n{BOLD}{GREEN}🎉 EXCELLENT!{RESET}")
        print(f"  All variables are configured correctly!")
        print(f"  Your deployment is production-ready! 🚀\n")

    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    # Return exit code
    return 0 if not critical_missing else 1

if __name__ == "__main__":
    exit(main())
