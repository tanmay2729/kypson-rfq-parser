# README.md - RFQ parser

## Approach
`parse_rfq()` is rule-based, using only Python's `re` module. The text is lower-cased and cleaned (`1,50,000` -> `150000`, `lac` -> `lakh`, `hazar` -> `hazaar`). Category comes from ordered keyword patterns (specific ones like fibc/bopp before generic ones like box). GSM and micron are read with regex. For quantity I look at every number, drop specs and dimensions (gsm, mic, inch, ply), treat kg/mt figures next to words like "capacity" or "bags" as fill weight, and pick the count (`40 hazaar`, `500 pcs`) as the order quantity. Location is matched against a city/country list, with fallbacks for unseen places ("to X", "X mein", the last word).

## Score on my_tests.jsonl
40/40 (100%) with the provided `score.py`. This is optimistic: I fixed the rules after seeing my own failures, so the hidden set will score lower.

## 3 messages it gets wrong
1. `need 5000 pcs boxes tomorrow` -> location "Tomorrow". The "last word is probably a place" fallback cannot tell a place from any other lowercase word it has not seen before.
2. `bopp bags 10000 pcs 65 gsm ahmednagar road` -> location "Road". It takes the last word, not the whole place phrase, so multi-word unseen places break.
3. `500 bopp bags and 200 corrugated boxes Pune` -> only the first product (bopp_bag, 500). The output has one category and one quantity, so a message with two products loses the second.

## With 1,000 real labelled examples
- Split into train/validation/test first, so scores are not measured on data I tuned on.
- Use a model for the fuzzy parts: a text classifier for category (character n-grams survive typos), and a token-level tagger (NER) for quantity, spec and place, instead of guessing from the last word.
- Keep rules for exact conversions (`lakh`, `hazaar`, unit normalisation), and use the labelled data to find which rules fail most often and to add a real list of Indian cities and towns.

## Knowing it works with real buyers
- Sample a few hundred live messages weekly, label them by hand, and track per-field accuracy, not only overall accuracy.
- Watch the share of messages where a field comes back empty, or where a seller or buyer corrects a field, as an early warning.
- Log every message the parser fails on and review them regularly; new spellings and cities will keep appearing.

## Tools
Python standard library only. I used Claude to help draft the test examples; I ran the tests, reviewed the code.
