"""Browser capability routing, not device attestation or an anti-cheat boundary."""
import re

def mobile_browser(user_agent, touch_hint=False):
    ua=user_agent or ''
    if re.search(r'Windows NT|CrOS',ua,re.I):return False
    if re.search(r'iPhone|iPod|iPad|Android',ua,re.I):return True
    return bool(touch_hint and 'Macintosh' in ua and 'Safari' in ua and 'Chrome' not in ua)
