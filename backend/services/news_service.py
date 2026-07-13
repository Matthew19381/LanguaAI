import logging

import feedparser

from backend.services.gemini_service import generate_json

logger = logging.getLogger(__name__)

# RSS feeds by language
RSS_FEEDS = {
    "German": [
        "https://www.dw.com/rss/rss.de.xml",
        "https://www.tagesschau.de/xml/rss2",
    ],
    "French": [
        "https://www.rfi.fr/fr/rss",
        "https://www.lemonde.fr/rss/une.xml",
    ],
    "Spanish": [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://www.bbc.co.uk/mundo/index.xml",
    ],
    "Italian": [
        "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
    ],
    "English": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "Portuguese": [
        "https://feeds.folha.uol.com.br/mundo/rss091.xml",
    ],
    "Dutch": [
        "https://feeds.nos.nl/nosnieuwsalgemeen",
    ],
    "Polish": [
        "https://www.polsatnews.pl/rss/wszystkie.xml",
    ],
    "Russian": [
        "https://www.voanews.com/api/zmmiqmmte_",
        "https://feeds.bbci.co.uk/russian/rss.xml",
    ],
}

DEFAULT_FEEDS = [
    "https://www.dw.com/rss/rss.en.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
]


def fetch_articles(language: str, limit: int = 10) -> list:
    """Fetch raw articles from RSS feeds for the given language."""
    feeds = RSS_FEEDS.get(language, DEFAULT_FEEDS)
    articles = []

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", entry.get("content", "")))
                # content may be a list of dicts
                if isinstance(summary, list) and summary:
                    summary = summary[0].get("value", "")
                link = entry.get("link", "")
                if title and summary:
                    articles.append({
                        "title": title,
                        "summary": summary[:600],
                        "link": link,
                        "source": feed.feed.get("title", feed_url),
                    })
                if len(articles) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Failed to fetch RSS feed {feed_url}: {e}")

        if len(articles) >= limit:
            break

    return articles[:limit]


async def simplify_article(article: dict, cefr_level: str, native_language: str, language: str) -> dict:
    """Use Gemini to simplify an article to the user's CEFR level."""
    prompt = f"""You are a language teacher. Simplify the following news article for a {language} learner at CEFR level {cefr_level} (native language: {native_language}).

Original article title: {article['title']}
Original summary: {article['summary']}

Create a simplified version appropriate for {cefr_level} level. Include:
1. A simplified title in {language}
2. A simplified text in {language} (80-120 words, using vocabulary appropriate for {cefr_level})
3. 5-8 key vocabulary words from the text with translations to {native_language}
4. 2 comprehension questions in {native_language}

Return JSON:
{{
    "title": "simplified title in {language}",
    "simplified_text": "simplified article text in {language}",
    "vocabulary": [
        {{"word": "...", "translation": "...", "cefr_level": "..."}}
    ],
    "comprehension_questions": [
        {{"question": "...", "answer": "..."}}
    ],
    "original_title": "{article['title']}",
    "source": "{article.get('source', '')}",
    "link": "{article.get('link', '')}"
}}"""

    try:
        result = await generate_json(prompt)
        result["original_link"] = article.get("link", "")
        result["source"] = article.get("source", "")
        return result
    except Exception as e:
        logger.error(f"Error simplifying article: {e}")
        return {
            "title": article["title"],
            "simplified_text": article["summary"],
            "vocabulary": [],
            "comprehension_questions": [],
            "original_title": article["title"],
            "source": article.get("source", ""),
            "link": article.get("link", ""),
            "original_link": article.get("link", ""),
        }


async def get_news_for_user(language: str, cefr_level: str, native_language: str, limit: int = 5) -> list:
    """Fetch and simplify news articles for the user."""
    raw_articles = fetch_articles(language, limit=limit + 5)
    if not raw_articles:
        # Fallback: generate sample news via Gemini
        return await _generate_sample_news(language, cefr_level, native_language, limit)

    results = []
    for article in raw_articles[:limit]:
        simplified = await simplify_article(article, cefr_level, native_language, language)
        results.append(simplified)

    return results


async def _generate_sample_news(language: str, cefr_level: str, native_language: str, limit: int) -> list:
    """Generate sample news articles using Gemini when RSS is unavailable."""
    prompt = f"""Generate {limit} sample news articles in {language} for a learner at CEFR level {cefr_level}.
Native language of learner: {native_language}

For each article, provide:
- A title in {language} appropriate for {cefr_level}
- A simplified text (80-100 words) in {language}
- 5 vocabulary words with {native_language} translations
- 2 comprehension questions

Return JSON:
{{
    "articles": [
        {{
            "title": "...",
            "simplified_text": "...",
            "vocabulary": [{{"word": "...", "translation": "...", "cefr_level": "..."}}],
            "comprehension_questions": [{{"question": "...", "answer": "..."}}],
            "source": "LinguaAI",
            "link": ""
        }}
    ]
}}"""

    try:
        result = await generate_json(prompt)
        return result.get("articles", [])
    except Exception as e:
        logger.error(f"Error generating sample news: {e}")
        return []
