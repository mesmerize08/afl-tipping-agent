import json
from data_fetcher import get_upcoming_fixtures, get_ladder, get_betting_odds, get_afl_news, compile_match_data
from predict import run_weekly_predictions
from tracker import check_and_update_results

# Step 1: Update last round's results
print("Checking last round results...")
summary = check_and_update_results()
if summary:
    print(f"Season accuracy: {summary.get('overall_accuracy_pct')}%")
else:
    print("No pending results to update.")

# Step 2: Generate this week's predictions
print("\nFetching fixtures...")
fixtures = get_upcoming_fixtures()
ladder   = get_ladder()
odds     = get_betting_odds()
news     = get_afl_news()

match_data  = [compile_match_data(g, ladder, odds) for g in fixtures]
predictions = run_weekly_predictions(match_data, news)

with open("predictions.json", "w") as f:
    json.dump(predictions, f, indent=2)

print(f"\nGenerated {len(predictions)} predictions")
for p in predictions:
    print(f"\n{'='*50}")
    print(f"🏉 {p['home_team']} vs {p['away_team']}")
    print(p['prediction'])