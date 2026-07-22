"""
Bot Detector - Analisis heuristico de cuentas para estimar % de bots/fakes.
Score 0-100 donde 100 = muy probable bot.
"""
import csv
import re
import os


def _score_username(username):
    """Score username for bot-like patterns."""
    score = 0
    if not username:
        return 20

    # Many consecutive digits
    digits = sum(1 for c in username if c.isdigit())
    if digits > len(username) * 0.5:
        score += 15
    elif digits > len(username) * 0.3:
        score += 8

    # Ends with many numbers (user12345678)
    trailing = re.search(r'\d{4,}$', username)
    if trailing:
        score += 12

    # Random-looking: mix of letters and numbers with no clear pattern
    if len(username) > 12 and digits > 3:
        score += 5

    # Underscores or dots everywhere
    special = sum(1 for c in username if c in '._')
    if special > 3:
        score += 5

    return min(score, 30)


def _score_name(full_name):
    """Score display name for bot-like patterns."""
    score = 0
    if not full_name or full_name.strip() == "":
        return 15

    # All lowercase or all uppercase (unusual for real names)
    if full_name == full_name.lower() and len(full_name) > 3:
        score += 3
    if full_name == full_name.upper() and len(full_name) > 3:
        score += 3

    # Contains promotional words
    promo_words = ["follow", "dm", "promo", "free", "click", "link", "buy",
                   "earn", "crypto", "bitcoin", "nft", "forex", "trade",
                   "money", "cash", "profit", "invest", "hot", "sexy",
                   "onlyfans", "dating", "single"]
    name_lower = full_name.lower()
    for word in promo_words:
        if word in name_lower:
            score += 10
            break

    # Has emojis (common in spam bots)
    emoji_count = len(re.findall(r'[\U00010000-\U0010ffff]', full_name))
    if emoji_count > 3:
        score += 5

    return min(score, 25)


def _score_metrics(followers, following, posts):
    """Score based on follower/following ratio and activity."""
    score = 0

    # No posts at all
    if posts == 0:
        score += 20

    # Following way more than followers (typical bot pattern)
    if following > 0 and followers > 0:
        ratio = followers / following
        if ratio < 0.01:  # 1:100+
            score += 20
        elif ratio < 0.05:
            score += 12
        elif ratio < 0.1:
            score += 6

    # Following zero people (weird for a real user interacting)
    if following == 0 and followers == 0:
        score += 15

    # Very high following count with very few posts
    if following > 5000 and posts < 5:
        score += 15

    return min(score, 30)


def _score_bio(bio):
    """Score bio for spam patterns."""
    score = 0
    if not bio or bio.strip() == "":
        score += 10
        return score

    bio_lower = bio.lower()

    # Spam indicators
    spam_words = ["dm for", "follow back", "f4f", "l4l", "follow me",
                  "click link", "link in bio", "onlyfans", "free followers",
                  "earn money", "bitcoin", "crypto", "forex", "trading",
                  "make money", "passive income", "dm me", "whatsapp",
                  "telegram group", "join now"]
    for word in spam_words:
        if word in bio_lower:
            score += 12
            break

    # URLs (many bots have shortened links)
    url_count = len(re.findall(r'https?://|bit\.ly|t\.co|goo\.gl|tinyurl', bio_lower))
    if url_count > 2:
        score += 8

    return min(score, 20)


def _score_profile_pic(has_pic):
    """Score based on whether profile has a picture."""
    if not has_pic:
        return 15
    return 0


def analyze_user(user_data):
    """
    Analyze a single user and return bot score (0-100).
    """
    username = user_data.get("username", "")
    full_name = user_data.get("full_name", "")
    bio = user_data.get("bio", "")
    followers = 0
    following = 0
    posts = 0
    has_pic = bool(user_data.get("profile_pic", ""))

    # Parse numeric fields
    for key in ["followers", "follower_count", "seguidores"]:
        val = user_data.get(key, "")
        if val:
            try:
                followers = int(str(val).replace(",", "").replace(".", ""))
            except ValueError:
                pass
            break

    for key in ["following", "following_count", "seguidos"]:
        val = user_data.get(key, "")
        if val:
            try:
                following = int(str(val).replace(",", "").replace(".", ""))
            except ValueError:
                pass
            break

    for key in ["posts", "post_count", "media_count", "publicaciones"]:
        val = user_data.get(key, "")
        if val:
            try:
                posts = int(str(val).replace(",", "").replace(".", ""))
            except ValueError:
                pass
            break

    # Calculate component scores
    s_username = _score_username(username)
    s_name = _score_name(full_name)
    s_metrics = _score_metrics(followers, following, posts)
    s_bio = _score_bio(bio)
    s_pic = _score_profile_pic(has_pic)

    total = min(s_username + s_name + s_metrics + s_bio + s_pic, 100)

    return {
        "username": username,
        "bot_score": total,
        "risk_level": "Alto" if total >= 60 else "Medio" if total >= 35 else "Bajo",
        "details": {
            "username_score": s_username,
            "name_score": s_name,
            "metrics_score": s_metrics,
            "bio_score": s_bio,
            "pic_score": s_pic,
        }
    }


def analyze_csv(csv_path):
    """
    Analyze all users in a CSV file and return bot analysis results.
    """
    if not os.path.exists(csv_path):
        return {"error": "CSV file not found", "results": []}

    results = []
    total_score = 0

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            analysis = analyze_user(row)
            results.append(analysis)
            total_score += analysis["bot_score"]

    total = len(results)
    avg_score = round(total_score / total, 1) if total > 0 else 0

    # Count by risk
    high = sum(1 for r in results if r["risk_level"] == "Alto")
    medium = sum(1 for r in results if r["risk_level"] == "Medio")
    low = sum(1 for r in results if r["risk_level"] == "Bajo")

    # Sort by score descending
    results.sort(key=lambda x: x["bot_score"], reverse=True)

    return {
        "total_analyzed": total,
        "average_score": avg_score,
        "risk_distribution": {
            "high": high,
            "medium": medium,
            "low": low,
        },
        "estimated_bot_pct": round(high / total * 100, 1) if total > 0 else 0,
        "results": results,
    }
