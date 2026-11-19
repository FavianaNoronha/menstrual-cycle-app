# Mining app-store reviews

We can't reach the Play Store from our build environment, so export reviews and run the script on them.

**Get the reviews (any of these):**
- Play Console doesn't give you competitors' reviews. Use a review exporter you trust (e.g. an Apify/AppBot export) for Flo, Clue, Period Tracker, Maya, Eve, and Indian apps, filtered to India and ratings 1-3.
- Or copy 200-300 reviews per app by hand into a CSV. It's slow but it works.

**CSV columns (header row required):** `app,rating,text` (extra columns are ignored).

**Run:**
```
python tools/mine_reviews.py reviews.csv            # theme counts + example lines
python tools/mine_reviews.py reviews.csv --examples 3
```
It reads only the file you give it and sends nothing anywhere. Themes are keyword-based (English plus common Hinglish words), so treat counts as a rough guide and read the example lines before believing any number. Add words to `THEMES` in the script as you see new phrasings. Review text is public; don't add reviewers' names to our notes.
