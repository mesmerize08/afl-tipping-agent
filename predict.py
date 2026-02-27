import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def format_form(form_list, team_name):
    """Format form into readable string."""
    if not form_list:
        return "No recent data available"
    
    results = []
    for g in form_list:
        results.append(f"{g['result']} vs {g['opponent']} ({g['score']}) on {g['date']}")
    
    wins = sum(1 for g in form_list if g['result'] == 'W')
    return f"{wins}/{len(form_list)} wins recently. " + " | ".join(results)

def format_h2h(h2h_list):
    """Format H2H into readable string."""
    if not h2h_list:
        return "No H2H data available"
    
    results = []
    for g in h2h_list[:5]:
        results.append(f"{g['winner']} won ({g['score']}) at {g['venue']} in {g['year']}")
    return " | ".join(results)

def format_ladder(ladder_data, team_name):
    """Format ladder position info."""
    if not ladder_data:
        return "Ladder data unavailable"
    
    pos = ladder_data.get("rank", "?")
    wins = ladder_data.get("wins", "?")
    losses = ladder_data.get("losses", "?")
    pct = ladder_data.get("percentage", "?")
    pts = ladder_data.get("pts", "?")
    return f"Position {pos} | {wins}W-{losses}L | {pts} pts | {pct}% percentage"

def generate_prediction(match_data, news_context=""):
    """Use Gemini to generate a prediction for a single match."""
    
    home = match_data["home_team"]
    away = match_data["away_team"]
    odds = match_data.get("betting_odds", {})
    
    # Build the odds section
    if odds:
        odds_text = f"""
BETTING ODDS (averaged across bookmakers):
- {home}: ${odds.get('home_odds', 'N/A')} (implied probability: {odds.get('home_implied_prob', 'N/A')}%)
- {away}: ${odds.get('away_odds', 'N/A')} (implied probability: {odds.get('away_implied_prob', 'N/A')}%)
"""
    else:
        odds_text = "BETTING ODDS: Not available this week."
    
    prompt = f"""
You are an expert AFL analyst. Analyse the following data for an upcoming AFL match and provide a data-driven, unbiased prediction.

=== MATCH DETAILS ===
Round {match_data['round']}: {home} vs {away}
Date: {match_data['date']}
Venue: {match_data['venue']}

=== LADDER STANDINGS ===
{home}: {format_ladder(match_data['home_ladder'], home)}
{away}: {format_ladder(match_data['away_ladder'], away)}

=== RECENT FORM (last 5 games) ===
{home}: {format_form(match_data['home_form'], home)}
{away}: {format_form(match_data['away_form'], away)}

=== HEAD TO HEAD (last 10 meetings) ===
{format_h2h(match_data['head_to_head'])}

=== VENUE RECORD at {match_data['venue']} (last 5 games each) ===
{home} at this venue: {format_form(match_data['home_venue_record'], home)}
{away} at this venue: {format_form(match_data['away_venue_record'], away)}

{odds_text}

=== RECENT AFL NEWS (for context on injuries/suspensions/team news) ===
{news_context[:1500] if news_context else "No news context available."}

=== YOUR TASK ===
Based ONLY on the data above, provide:

1. **PREDICTED WINNER**: State clearly which team you predict to win.
2. **WIN PROBABILITY**: Your estimated probability (e.g., {home}: 62%, {away}: 38%). Do NOT just copy the betting implied probability — use it as one input alongside all other factors.
3. **MARGIN**: Estimated winning margin in points.
4. **KEY FACTORS**: The 3-4 most important data-driven reasons for your prediction.
5. **CONFIDENCE**: Rate your confidence as Low / Medium / High and explain why.
6. **RISKS**: What could cause the underdog to win?

Be analytical, specific, and reference the actual data. Do not be vague. Format your response clearly with the headers above.
"""
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating prediction: {e}"

def run_weekly_predictions(match_data_list, news_headlines):
    """Run predictions for all this week's matches."""
    
    # Format news into a single context block
    news_context = ""
    for item in news_headlines[:10]:
        news_context += f"• {item['title']}: {item['summary']}\n"
    
    all_predictions = []
    
    for match in match_data_list:
        print(f"🏉 Predicting: {match['home_team']} vs {match['away_team']}...")
        prediction_text = generate_prediction(match, news_context)
        
        all_predictions.append({
            "round": match["round"],
            "date": match["date"],
            "venue": match["venue"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "betting_odds": match.get("betting_odds", {}),
            "prediction": prediction_text
        })
    
    return all_predictions