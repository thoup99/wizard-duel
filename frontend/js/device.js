export function isLikelyPhone(env = window) {
  const nav = env.navigator,
    ua = nav.userAgent || "",
    touch = nav.maxTouchPoints || 0;
  if (/Windows NT|CrOS/i.test(ua)) return false;
  if (/iPhone|iPad|iPod|Android/i.test(ua)) return true;
  if (nav.userAgentData?.mobile === true) return true;
  return nav.platform === "MacIntel" && touch > 1;
}
