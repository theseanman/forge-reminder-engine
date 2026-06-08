#!/usr/bin/env python3
"""
FORGE OS Daily Brief Generator - GITHUB ACTIONS VERSION
No interactive prompts. Reads Welltory/Sleep from data.json.
Fetches weather and calendar automatically.
Saves index.html for GitHub Pages.
"""

import os
import json
import caldav
import vobject
import urllib.request
from datetime import datetime, date, timedelta, timezone

RICHMOND_COORDS = (49.1895, -123.1724)
ICLOUD_EMAIL = os.environ.get("ICLOUD_EMAIL", "yoseanreid@icloud.com")
ICLOUD_PASSWORD = os.environ.get("ICLOUD_PASSWORD", "")

def load_user_data():
    """Load Welltory + Sleep data from data.json."""
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except:
        return {
            "welltory": {"stress": 50, "energy": 50, "health": 50},
            "sleep": {"score": 85, "duration": "7h 0m", "hr_range": "50–70"}
        }

def get_weather():
    """Fetch weather for Richmond, BC."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={RICHMOND_COORDS[0]}&longitude={RICHMOND_COORDS[1]}&current=temperature_2m,weather_code&temperature_unit=celsius&timezone=America/Vancouver"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            temp = data.get("current", {}).get("temperature_2m", "N/A")
            code = data.get("current", {}).get("weather_code", 0)
            desc = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Foggy",51:"Light drizzle",61:"Slight rain",80:"Rain showers",95:"Thunderstorm"}.get(code, "Cloudy")
            return f"{desc}, {temp}°C"
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return "Weather unavailable"

def fetch_events_for_range(calendars, start, end):
    """Fetch and format events for a given date range."""
    all_events = []
    for calendar in calendars:
        try:
            events = calendar.date_search(start=start, end=end, expand=True)
            for event in events:
                try:
                    vevent = event.vobject_instance.vevent
                    summary = str(vevent.summary.value) if hasattr(vevent, 'summary') else "Event"
                    dtstart = vevent.dtstart.value
                    if hasattr(dtstart, 'hour'):
                        all_events.append((str(dtstart), f"{summary} @ {dtstart.strftime('%a %b %d, %I:%M %p')}"))
                    else:
                        all_events.append((str(dtstart), f"{summary} — {dtstart.strftime('%a %b %d')} (All Day)"))
                except:
                    continue
        except:
            continue
    all_events.sort(key=lambda x: x[0])
    return [e[1] for e in all_events]

def get_calendar_events():
    """Fetch today, week, and month events from iCloud via CalDAV."""
    if not ICLOUD_PASSWORD:
        return {"today": "No iCloud password configured.", "week": "", "month": ""}
    
    try:
        client = caldav.DAVClient(
            url="https://caldav.icloud.com",
            username=ICLOUD_EMAIL,
            password=ICLOUD_PASSWORD
        )
        
        principal = client.principal()
        calendars = principal.calendars()
        
        today = date.today()
        tz = timezone.utc

        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        today_end = datetime.combine(today + timedelta(days=1), datetime.min.time()).replace(tzinfo=tz)
        week_end = datetime.combine(today + timedelta(days=7), datetime.min.time()).replace(tzinfo=tz)
        month_end = datetime.combine(today + timedelta(days=30), datetime.min.time()).replace(tzinfo=tz)

        today_events = fetch_events_for_range(calendars, today_start, today_end)
        week_events = fetch_events_for_range(calendars, today_start, week_end)
        month_events = fetch_events_for_range(calendars, today_start, month_end)

        print(f"✓ Today: {len(today_events)} | Week: {len(week_events)} | Month: {len(month_events)} events")

        return {
            "today": "\n".join(today_events) if today_events else "No events today.",
            "week": "\n".join(week_events) if week_events else "No events this week.",
            "month": "\n".join(month_events) if month_events else "No events this month."
        }

    except Exception as e:
        print(f"Calendar fetch failed: {e}")
        return {"today": "Calendar unavailable.", "week": "", "month": ""}

def get_character_quote(day_of_week):
    characters = [
        {"name": "Hannibal Smith", "quote": "You know, Murdock, sometimes the best plans are the ones that seem the craziest.", "show": "The A-Team", "image": "https://upload.wikimedia.org/wikipedia/en/thumb/d/da/Hannibal_Smith.jpg/220px-Hannibal_Smith.jpg"},
        {"name": "Zack Morris", "quote": "The more rules they make, the more ways I find to get around them.", "show": "Saved by the Bell", "image": "https://upload.wikimedia.org/wikipedia/en/thumb/0/0f/Zack_Morris.jpg/220px-Zack_Morris.jpg"},
        {"name": "Eddie Haskell", "quote": "Gee Beaver, I'd love to help, but something just came up that's ever so important.", "show": "Leave it to Beaver", "image": "https://upload.wikimedia.org/wikipedia/en/thumb/3/32/Eddie_Haskell.jpg/220px-Eddie_Haskell.jpg"},
        {"name": "Al Bundy", "quote": "I had it all once. Now I'm married with children. But I didn't have it all—I had something better.", "show": "Married... with Children", "image": "https://upload.wikimedia.org/wikipedia/en/thumb/c/c5/Al_Bundy.jpg/220px-Al_Bundy.jpg"}
    ]
    return characters[day_of_week % len(characters)]

def generate_html(welltory, sleep, weather, calendar_events):
    now = datetime.now()
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    day_of_week = now.weekday()

    stress_status = "Elevated" if welltory["stress"] >= 60 else "Moderate" if welltory["stress"] >= 40 else "Low"
    energy_status = "High" if welltory["energy"] >= 60 else "Moderate" if welltory["energy"] >= 40 else "Limited"
    health_status = "Optimal" if welltory["health"] >= 60 else "Vulnerable" if welltory["health"] >= 30 else "At Risk"

    if welltory["stress"] >= 70 or welltory["energy"] <= 40:
        mode = "RECOVERY DAY PROTOCOL ACTIVE"
        mode_advice = f"Health at risk. Stress {welltory['stress']}% (elevated). Energy {welltory['energy']}% (limited). No strain. No decisions. Rest only."
    elif welltory["stress"] >= 50:
        mode = "CHILL FLOW ACTIVE"
        mode_advice = "Moderate pace. Defer big decisions. Protect energy."
    else:
        mode = "NORMAL PROTOCOL ACTIVE"
        mode_advice = "Execute as planned. Stay sharp."

    char = get_character_quote(day_of_week)

    cal_today = calendar_events.get("today", "No events today.")
    cal_week = calendar_events.get("week", "No events this week.")
    cal_month = calendar_events.get("month", "No events this month.")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <title>FORGE OS · Morning Brief</title>
  <style>
    :root {{
      --text-light: #1a1a1a;
      --text-bright: #0d0d0d;
      --muted: #4a4a4a;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ -webkit-text-size-adjust: 100%; }}
    body {{ 
      background: linear-gradient(135deg, #d84315 0%, #ff9800 50%, #ffc107 100%);
      color: var(--text-light);
      font-family: -apple-system, 'Segoe UI', Tahoma, sans-serif;
      min-height: 100vh;
      padding: 20px;
    }}
    .shell {{ max-width: 95vw; margin: 0 auto; }}
    @media screen and (orientation: landscape) {{
      .shell {{ max-width: 98vw; }}
      .advice-grid {{ grid-template-columns: 1fr 1fr 1fr; }}
      body {{ padding: 12px; }}
    }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 4px solid var(--text-bright); }}
    .forge-label {{ font-size: 26px; letter-spacing: 0.3em; color: var(--text-bright); font-weight: 700; text-transform: uppercase; }}
    .forge-sub {{ font-size: 18px; color: var(--muted); margin-top: 6px; }}
    .date-block {{ text-align: right; }}
    .date-main {{ font-size: 28px; color: var(--text-bright); font-weight: 700; }}
    .date-time {{ font-size: 16px; color: var(--muted); margin-top: 4px; }}
    .card {{ background: rgba(255,255,255,0.15); border: 3px solid var(--text-bright); border-radius: 12px; padding: 18px; margin-bottom: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }}
    .card-header {{ font-size: 16px; letter-spacing: 0.2em; color: var(--text-bright); text-transform: uppercase; margin-bottom: 14px; font-weight: 700; display: flex; align-items: center; gap: 10px; }}
    .card-icon {{ font-size: 32px; }}
    .stat-row {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px; }}
    .stat-block {{ background: rgba(255,255,255,0.2); border: 2px solid var(--text-bright); border-radius: 8px; padding: 14px 10px; text-align: center; }}
    .stat-val {{ font-size: 32px; font-weight: 700; line-height: 1; color: var(--text-bright); }}
    .stat-label {{ font-size: 13px; letter-spacing: 0.12em; color: var(--muted); text-transform: uppercase; margin-top: 6px; }}
    .stat-sub {{ font-size: 13px; margin-top: 4px; font-weight: 600; }}
    .motd-box {{ background: rgba(255,255,255,0.15); border: 3px solid var(--text-bright); border-radius: 12px; padding: 16px; margin-bottom: 14px; }}
    .motd-text {{ font-size: 22px; color: var(--text-bright); line-height: 1.8; font-style: italic; font-weight: 500; }}
    .motd-source {{ font-size: 16px; color: var(--text-light); margin-top: 8px; font-weight: 600; }}
    .character-quote-box {{ background: rgba(255,255,255,0.15); border: 3px solid var(--text-bright); border-radius: 12px; padding: 16px; margin-bottom: 14px; display: grid; grid-template-columns: 100px 1fr; gap: 16px; align-items: center; }}
    .character-image {{ width: 100px; height: 100px; border-radius: 8px; border: 2px solid var(--text-bright); object-fit: cover; }}
    .character-quote {{ font-size: 17px; color: var(--text-bright); font-style: italic; font-weight: 500; margin-bottom: 8px; }}
    .character-name {{ font-size: 13px; color: var(--text-light); font-weight: 600; }}
    .alert-banner {{ background: rgba(255,50,50,0.3); border: 3px solid var(--text-bright); border-radius: 8px; padding: 14px; font-size: 15px; color: var(--text-bright); margin-bottom: 14px; line-height: 1.7; font-weight: 600; }}
    .input-banner {{ background: rgba(255,255,255,0.2); border: 3px solid var(--text-bright); border-radius: 8px; padding: 14px; font-size: 15px; color: var(--text-bright); margin-bottom: 14px; line-height: 1.7; font-weight: 600; text-align: center; }}
    .input-banner a {{ color: var(--text-bright); font-size: 17px; }}
    .mini-card {{ background: rgba(255,255,255,0.12); border: 2px solid var(--text-bright); border-radius: 8px; padding: 12px; margin-bottom: 10px; }}
    .mini-title {{ font-size: 15px; color: var(--text-bright); font-weight: 700; margin-bottom: 6px; }}
    .mini-detail {{ font-size: 13px; color: var(--text-light); line-height: 1.6; }}
    .paramount-goal {{ background: rgba(255,255,255,0.2); border: 2px solid var(--text-bright); border-radius: 8px; padding: 14px; margin-bottom: 10px; font-size: 14px; color: var(--text-light); line-height: 1.7; font-weight: 600; }}
    .paramount-num {{ font-size: 15px; color: var(--text-bright); font-weight: 700; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
    .goal-controls {{ display: flex; gap: 8px; align-items: center; }}
    .goal-btn {{ background: rgba(255,255,255,0.4); border: 2px solid var(--text-bright); border-radius: 6px; padding: 8px 16px; font-weight: 700; font-size: 20px; color: var(--text-bright); cursor: pointer; touch-action: manipulation; min-width: 44px; min-height: 44px; display: flex; align-items: center; justify-content: center; }}
    .goal-btn:active {{ background: rgba(255,255,255,0.7); }}
    .goal-counter {{ background: rgba(255,255,255,0.3); border: 2px solid var(--text-bright); border-radius: 6px; padding: 6px 14px; font-weight: 700; font-size: 16px; min-width: 40px; text-align: center; color: var(--text-bright); }}
    .advice-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .advice-item {{ background: rgba(255,255,255,0.1); border: 2px solid var(--text-bright); border-radius: 8px; padding: 12px; }}
    .advice-label {{ font-size: 12px; font-weight: 700; color: var(--text-bright); text-transform: uppercase; margin-bottom: 6px; }}
    .advice-text {{ font-size: 13px; color: var(--text-light); line-height: 1.5; }}
    .footer {{ text-align: center; margin-top: 20px; font-size: 11px; color: var(--muted); letter-spacing: 0.15em; padding-bottom: 30px; }}
    a {{ color: var(--text-bright); text-decoration: none; font-weight: 700; border-bottom: 2px solid var(--text-bright); }}
    .expandable {{ cursor: pointer; }}
    .expandable-content {{ display: none; font-size: 14px; color: var(--text-light); line-height: 1.7; margin-top: 10px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 4px; }}
  </style>
</head>
<body>
<div class="shell">

  <div class="topbar">
    <div>
      <div class="forge-label">🌴 FORGE OS 🌴</div>
      <div class="forge-sub">Morning Brief</div>
    </div>
    <div class="date-block">
      <div class="date-main">{day_name}</div>
      <div style="font-size:11px; color:var(--muted);">{date_str}</div>
      <div class="date-time" id="live-clock">{time_str}</div>
    </div>
  </div>

  <div class="input-banner">
    📊 Update today's HRV + Sleep data → <a href="https://theseanman.github.io/forge-daily-brief/input.html">Open Input Form →</a>
  </div>

  <div class="motd-box">
    <div class="motd-text">"You have power over your mind—not outside events. Realize this, and you will find strength."</div>
    <div class="motd-source">— Marcus Aurelius, Meditations</div>
  </div>

  <div class="character-quote-box">
    <img class="character-image" src="{char['image']}" alt="{char['name']}" onerror="this.style.display='none'">
    <div>
      <div class="character-quote">"{char['quote']}"</div>
      <div class="character-name">— {char['name']}, {char['show']}</div>
    </div>
  </div>

  <div class="alert-banner">🚨 {mode} {mode_advice}</div>

  <div class="card">
    <div class="card-header"><span class="card-icon">❤️🌴</span><span>Welltory HRV</span></div>
    <div class="stat-row">
      <div class="stat-block"><div class="stat-val">{welltory['stress']}%</div><div class="stat-label">Stress</div><div class="stat-sub">{stress_status}</div></div>
      <div class="stat-block"><div class="stat-val">{welltory['energy']}%</div><div class="stat-label">Energy</div><div class="stat-sub">{energy_status}</div></div>
      <div class="stat-block"><div class="stat-val">{welltory['health']}%</div><div class="stat-label">Health</div><div class="stat-sub">{health_status}</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">😴🌴</span><span>Sleep Report</span></div>
    <div class="stat-row">
      <div class="stat-block"><div class="stat-val">{sleep['score']}%</div><div class="stat-label">Score</div></div>
      <div class="stat-block"><div class="stat-val">{sleep['duration']}</div><div class="stat-label">Duration</div></div>
      <div class="stat-block"><div class="stat-val">{sleep['hr_range']}</div><div class="stat-label">HR Range</div></div>
    </div>
  </div>

  <div class="card" style="background: linear-gradient(135deg, rgba(255,215,0,0.25), rgba(255,140,0,0.15)); border: 3px double var(--text-bright);">
    <div class="card-header"><span class="card-icon">🎯🌴</span><span>Five Paramount Goals</span></div>
    <div class="paramount-goal">
      <div class="paramount-num"><span>1️⃣ PAUSE BEFORE ANSWERING</span>
        <div class="goal-controls">
          <button class="goal-btn" onclick="decrementGoal(0)">−</button>
          <span class="goal-counter" id="goal-0-counter">0</span>
          <button class="goal-btn" onclick="incrementGoal(0)">+</button>
        </div>
      </div>
      Brief pause before any response. Conscious deliberation first.
    </div>
    <div class="paramount-goal">
      <div class="paramount-num"><span>2️⃣ CAL AI BEFORE MEALS</span>
        <div class="goal-controls">
          <button class="goal-btn" onclick="decrementGoal(1)">−</button>
          <span class="goal-counter" id="goal-1-counter">0</span>
          <button class="goal-btn" onclick="incrementGoal(1)">+</button>
        </div>
      </div>
      Log nutrition in Cal AI before eating. Every meal. Non-negotiable.
    </div>
    <div class="paramount-goal">
      <div class="paramount-num"><span>3️⃣ SLOW MOVEMENTS & SPEECH</span>
        <div class="goal-controls">
          <button class="goal-btn" onclick="decrementGoal(2)">−</button>
          <span class="goal-counter" id="goal-2-counter">0</span>
          <button class="goal-btn" onclick="incrementGoal(2)">+</button>
        </div>
      </div>
      Deliberate, slower pace in all physical and verbal communication.
    </div>
    <div class="paramount-goal">
      <div class="paramount-num"><span>4️⃣ OPPORTUNITY SCANNING</span>
        <div class="goal-controls">
          <button class="goal-btn" onclick="decrementGoal(3)">−</button>
          <span class="goal-counter" id="goal-3-counter">0</span>
          <button class="goal-btn" onclick="incrementGoal(3)">+</button>
        </div>
      </div>
      Every setback: "What opportunity does this situation present me with?"
    </div>
    <div class="paramount-goal">
      <div class="paramount-num"><span>5️⃣ NO NARRATIVES</span>
        <div class="goal-controls">
          <button class="goal-btn" onclick="decrementGoal(4)">−</button>
          <span class="goal-counter" id="goal-4-counter">0</span>
          <button class="goal-btn" onclick="incrementGoal(4)">+</button>
        </div>
      </div>
      Shut down internal narratives the moment they begin. Facts only.
    </div>
    <div class="mini-detail" style="margin-top:12px; font-size:12px; color:var(--muted);">💡 Tap +/− to track. Counters reset at midnight.</div>
  </div>

  <div class="card" style="background: linear-gradient(135deg, rgba(100,150,200,0.2), rgba(70,120,170,0.1)); border: 3px solid var(--text-bright);">
    <div class="card-header"><span class="card-icon">🎭🌴</span><span>Identityless Protocol</span></div>
    <div class="mini-card expandable" onclick="toggleSection(this)">
      <div class="mini-title">🌀 Tap to expand</div>
      <div class="expandable-content">
        <strong>GROUNDLESSNESS TOLERANCE:</strong><br>
        • No-Frame Actions: Act without identity narratives. Just do it.<br>
        • "I Don't Know" as Full Stop: Sit in uncertainty 30–60 seconds.<br>
        • "No Story. Just This": Cut narrative, focus on sensory data.<br><br>
        <strong>INTERNAL AUDIENCE REMOVAL:</strong><br>
        • Catching "Camera On": Detect self-observation, label it, don't judge.<br>
        • Shift to Raw Perception: Anchor in ONE sensory channel.<br>
        • Unwitnessed Existence: 2–5 min activities with zero self-reference.
      </div>
    </div>
  </div>

  <div class="card" style="background: linear-gradient(135deg, rgba(150,100,200,0.2), rgba(120,70,170,0.1)); border: 3px solid var(--text-bright);">
    <div class="card-header"><span class="card-icon">⏰🌴</span><span>Future Self Protocol</span></div>
    <div class="mini-card expandable" onclick="toggleSection(this)">
      <div class="mini-title">📋 Tap to expand</div>
      <div class="expandable-content">
        <strong>MORNING:</strong> Posture Reset → Fractal Scan → Identity Merge → EV Selection → Atmospheric Bruiser Lock-In<br><br>
        <strong>MIDDAY:</strong> Re-anchor → SBOS scan → Remove friction → Enforce boundary → Execute micro-win<br><br>
        <strong>EVENING:</strong> What aligned? What violated? What friction needs removal? What system needs upgrading?
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">🌤️🌴</span><span>Richmond Weather</span></div>
    <div class="mini-card"><div class="mini-detail">{weather}</div></div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">📅🌴</span><span>Today — {date_str}</span></div>
    <div class="mini-card"><div class="mini-detail"><pre style="font-size:13px; color:var(--text-light); white-space:pre-wrap; word-wrap:break-word; font-family:-apple-system,sans-serif;">{cal_today}</pre></div></div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">📆🌴</span><span>This Week (Next 7 Days)</span></div>
    <div class="mini-card"><div class="mini-detail"><pre style="font-size:13px; color:var(--text-light); white-space:pre-wrap; word-wrap:break-word; font-family:-apple-system,sans-serif;">{cal_week}</pre></div></div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">🗓️🌴</span><span>This Month (Next 30 Days)</span></div>
    <div class="mini-card expandable" onclick="toggleSection(this)">
      <div class="mini-title">Tap to expand</div>
      <div class="expandable-content"><pre style="font-size:13px; color:var(--text-light); white-space:pre-wrap; word-wrap:break-word; font-family:-apple-system,sans-serif;">{cal_month}</pre></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">💡🌴</span><span>Quick Actionable Wisdom</span></div>
    <div class="advice-grid">
      <div class="advice-item"><div class="advice-label">🥋 Self-Defense</div><div class="advice-text">Stance is survival. Feet shoulder-width, weight distributed, knees soft. Stability beats speed.</div></div>
      <div class="advice-item"><div class="advice-label">👨‍👧‍👦 Parenting</div><div class="advice-text">Listen more than talk. Your daughters don't need perfect—they need present.</div></div>
      <div class="advice-item"><div class="advice-label">👨 Fatherhood</div><div class="advice-text">Model recovery. Show them that rest and saying "not today" is strength.</div></div>
      <div class="advice-item"><div class="advice-label">🧠 Mindset</div><div class="advice-text">When the narrative starts: "Story activated." Drop it. Three words. Reset.</div></div>
      <div class="advice-item"><div class="advice-label">⏳ Longevity</div><div class="advice-text">3–4L water + electrolytes. Your immune system's operating capital. Log in Cal AI.</div></div>
      <div class="advice-item"><div class="advice-label">⚡ Life Hack</div><div class="advice-text">Batch texts/emails. Check noon and 5 PM only. Attention is finite.</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">🇯🇵🌴</span><span>Japanese Word of the Day</span></div>
    <div class="mini-card">
      <div class="mini-title">今日の言葉: 刹那 (Setsuna) — JLPT N1</div>
      <div class="mini-detail">
        A fleeting moment; the infinitesimal instant.<br>
        人生は刹那の連続だ = "Life is a succession of fleeting moments."<br>
        <strong>Today:</strong> Recovery happens setsuna by setsuna.
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-icon">🎨🌴</span><span>Art & Music</span></div>
    <div class="mini-card">
      <div class="mini-title">🎨 Kusama Yayoi — Infinity Mirror Room</div>
      <div class="mini-detail">
        <a href="https://artsandculture.google.com/search?q=kusama+infinity+mirror" target="_blank">Google Arts & Culture →</a> &nbsp;
        <a href="https://www.guggenheim.org/exhibitions/yayoi-kusama" target="_blank">Guggenheim →</a>
      </div>
    </div>
    <div class="mini-card">
      <div class="mini-title">🎵 Sarcófago — I.N.R.I. (1987)</div>
      <div class="mini-detail">
        <a href="https://open.spotify.com/search/sarcofago%20inri" target="_blank">Spotify →</a> &nbsp;
        <a href="https://music.youtube.com/search?q=sarcofago+inri" target="_blank">YouTube Music →</a>
      </div>
    </div>
  </div>

  <div class="footer">🌴 FORGE OS · {date_str.upper()} · {time_str} · theseanman.github.io/forge-daily-brief</div>

</div>

<script>
var counts = [0,0,0,0,0];
function loadCounts() {{
  var today = new Date().toDateString();
  try {{
    if (localStorage.getItem('forge-date') === today) {{
      for (var i = 0; i < 5; i++) {{
        var v = localStorage.getItem('g' + i);
        if (v) counts[i] = parseInt(v);
      }}
    }} else {{
      for (var i = 0; i < 5; i++) localStorage.removeItem('g' + i);
      localStorage.setItem('forge-date', today);
    }}
  }} catch(e) {{}}
  for (var i = 0; i < 5; i++) {{
    var el = document.getElementById('goal-' + i + '-counter');
    if (el) el.textContent = counts[i];
  }}
}}
function incrementGoal(i) {{
  counts[i]++;
  try {{ localStorage.setItem('g' + i, counts[i]); }} catch(e) {{}}
  document.getElementById('goal-' + i + '-counter').textContent = counts[i];
}}
function decrementGoal(i) {{
  if (counts[i] > 0) counts[i]--;
  try {{ localStorage.setItem('g' + i, counts[i]); }} catch(e) {{}}
  document.getElementById('goal-' + i + '-counter').textContent = counts[i];
}}
function toggleSection(el) {{
  var c = el.querySelector('.expandable-content');
  if (c) c.style.display = c.style.display === 'block' ? 'none' : 'block';
}}
function tick() {{
  var el = document.getElementById('live-clock');
  if (el) {{
    var now = new Date();
    el.textContent = now.toLocaleTimeString('en-US', {{hour:'2-digit',minute:'2-digit'}});
  }}
}}
window.onload = function() {{ loadCounts(); setInterval(tick, 1000); }};
</script>
</body>
</html>"""
    return html

def main():
    print("🌴 FORGE OS GitHub Actions Brief Generator")
    
    user_data = load_user_data()
    welltory = user_data.get("welltory", {"stress": 50, "energy": 50, "health": 50})
    sleep = user_data.get("sleep", {"score": 85, "duration": "7h 0m", "hr_range": "50–70"})
    
    print(f"✓ Loaded user data: Stress {welltory['stress']}%, Energy {welltory['energy']}%, Health {welltory['health']}%")
    
    weather = get_weather()
    calendar = get_calendar_events()
    
    html = generate_html(welltory, sleep, weather, calendar)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("✅ index.html generated successfully")

if __name__ == "__main__":
    main()
