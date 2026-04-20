import json
from data_fetcher import (get_upcoming_fixtures, get_ladder, get_betting_odds,
                           get_afl_news, compile_match_data, get_squiggle_tips)
from predict import run_weekly_predictions
from tracker import check_and_update_results

# Step 1: Update last round's results
print("Checking last round results...")
summary = check_and_update_results()
if summary:
    print(f"Season accuracy: {summary.get('overall_accuracy_pct')}%")
else:
    print("No pending results to update.")

# Step 2: Fetch this week's fixtures and supporting data
print("\nFetching fixtures...")
fixtures = get_upcoming_fixtures()
round_num = fixtures[0].get("round") if fixtures else None

ladder        = get_ladder()
odds          = get_betting_odds()
news          = get_afl_news()
squiggle_tips = get_squiggle_tips(round_number=round_num)

match_data  = [compile_match_data(g, ladder, odds, squiggle_tips=squiggle_tips)
               for g in fixtures]
predictions = run_weekly_predictions(match_data, news)

with open("predictions.json", "w") as f:
    json.dump(predictions, f, indent=2)

print(f"\nGenerated {len(predictions)} predictions")
for p in predictions:
    print(f"\n{'='*50}")
    print(f"🏉 {p['home_team']} vs {p['away_team']}")
    print(p['prediction'])
