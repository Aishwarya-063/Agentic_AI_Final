import asyncio
import json
import re
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="NestIQ Lite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: Dict[str, Dict[str, Any]] = {}

class OnboardingAnswers(BaseModel):
    profile_type: str
    destination: str
    budget: int
    move_timeline: str
    work_style: str
    pets: str
    lifestyle: str
    dealbreakers: str

class UserProfile(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile_type: str
    destination_city: str
    monthly_budget: int
    move_timeline: str
    work_style: str
    pets: str
    lifestyle_priorities: List[str]
    dealbreakers: List[str]

class ChatRequest(BaseModel):
    message: str

QUESTIONS = [
    {"id": "profile_type", "question": "Which relocation profile best matches you?", "helper": "Remote worker, young family, career relocator, or empty nester"},
    {"id": "destination", "question": "Where are you moving?", "helper": "Example: Chicago, Austin, New York"},
    {"id": "budget", "question": "What is your monthly rent budget?", "helper": "Example: 1800"},
    {"id": "move_timeline", "question": "When are you moving?", "helper": "Example: in 6 weeks, next month, August 1"},
    {"id": "work_style", "question": "What is your work situation?", "helper": "Remote, hybrid, or in-office?"},
    {"id": "pets", "question": "Any pets coming with you?", "helper": "Example: one dog, two cats, no pets"},
    {"id": "lifestyle", "question": "What kind of lifestyle do you want nearby?", "helper": "Example: coffee shops, parks, quiet streets, nightlife, walkability"},
    {"id": "dealbreakers", "question": "What are your dealbreakers?", "helper": "Example: noise, long commute, unsafe at night, no parking"},
]

NEIGHBORHOOD_LIBRARY = {
    "chicago": [
        {
            "name": "Logan Square", "slug": "logan-square", "score": 89,
            "pros": ["excellent coffee scene", "dog-friendly streets", "strong restaurant access"],
            "cons": ["weekend noise near Milwaukee Ave", "popular units move quickly"],
            "watchout": "Choose residential blocks if you hate noise.",
            "vibe": "Logan Square feels creative, social, and walkable. It works especially well for a remote worker who wants coffee shops, neighborhood energy, and dog-friendly routines. The trade-off is noise: the closer you are to Milwaukee Avenue, the more weekend activity you will feel.",
            "tags": ["coffee-heavy", "dog-friendly", "creative", "lively-weekends"]
        },
        {
            "name": "Andersonville", "slug": "andersonville", "score": 84,
            "pros": ["calmer residential feel", "independent shops", "good for pets"],
            "cons": ["farther from downtown", "fewer late-night options"],
            "watchout": "Commute can feel longer if you need to be downtown often.",
            "vibe": "Andersonville feels warm, local, and lived-in. It is quieter than trendier nightlife-heavy areas but still has great coffee, groceries, restaurants, and parks. For someone who dislikes noise and has a dog, this is one of the safer lifestyle fits.",
            "tags": ["quiet", "local-shops", "dog-friendly", "remote-friendly"]
        },
        {
            "name": "Ravenswood", "slug": "ravenswood", "score": 78,
            "pros": ["quiet streets", "good transit access", "more space for budget"],
            "cons": ["less energetic", "fewer iconic going-out spots"],
            "watchout": "Great fit if calm matters more than nightlife.",
            "vibe": "Ravenswood is practical, calm, and comfortable. It does not try too hard to be cool, which is exactly the point. You get coffee shops, access to transit, and quieter apartment options without feeling isolated from the city.",
            "tags": ["quiet", "practical", "transit-access", "good-value"]
        },
    ],
    "austin": [
        {
            "name": "Mueller", "slug": "mueller", "score": 88,
            "pros": ["parks", "walkable pockets", "good for dogs"],
            "cons": ["can be pricey", "limited bargain inventory"],
            "watchout": "Check total monthly cost carefully.",
            "vibe": "Mueller feels planned, green, and easy to live in. It is strong for remote workers, pet owners, and people who want daily errands nearby. It is not the cheapest choice, but the convenience is real.",
            "tags": ["green-space", "dog-friendly", "planned", "remote-friendly"]
        },
        {
            "name": "Hyde Park", "slug": "hyde-park", "score": 82,
            "pros": ["coffee shops", "older charm", "central location"],
            "cons": ["older buildings", "parking can be annoying"],
            "watchout": "Inspect older units carefully.",
            "vibe": "Hyde Park feels academic, cozy, and neighborhood-first. It is a good choice for someone who wants coffee shops and calm streets, though older apartments can have maintenance surprises.",
            "tags": ["coffee", "quiet", "central", "older-buildings"]
        },
        {
            "name": "Crestview", "slug": "crestview", "score": 77,
            "pros": ["calm", "residential", "good value"],
            "cons": ["less nightlife", "car may be useful"],
            "watchout": "Better if you value quiet over constant activity.",
            "vibe": "Crestview is steady, quiet, and practical. It is not flashy, but it gives you breathing room, neighborhood comfort, and lower stress than the louder central areas.",
            "tags": ["quiet", "residential", "good-value", "low-stress"]
        },
    ]
}

DEFAULT_NEIGHBORHOODS = [
    {
        "name": "Central District", "slug": "central-district", "score": 82,
        "pros": ["good access", "active streets", "easy errands"],
        "cons": ["higher rent", "more noise"],
        "watchout": "Good convenience, but check noise before signing.",
        "vibe": "This area is the safest general recommendation when the app does not yet have city-specific data. It balances access, amenities, and rental availability, but you should verify street-level noise and total monthly cost.",
        "tags": ["convenient", "amenities", "active", "verify-noise"]
    },
    {
        "name": "Northside Residential", "slug": "northside-residential", "score": 78,
        "pros": ["quieter", "more residential", "better space"],
        "cons": ["less central", "fewer late-night options"],
        "watchout": "Commute may be the trade-off.",
        "vibe": "This is the calmer option. It works for users who want quieter streets, better value, and a more settled routine instead of nightlife or constant activity.",
        "tags": ["quiet", "residential", "value", "settled"]
    },
    {
        "name": "Arts & Market Quarter", "slug": "arts-market-quarter", "score": 75,
        "pros": ["food", "cafes", "energy"],
        "cons": ["noise", "variable prices"],
        "watchout": "Best for energy, not silence.",
        "vibe": "This neighborhood has the strongest lifestyle pull: cafes, food, local businesses, and movement. It may be too loud for someone who explicitly wants quiet, but it can be exciting if energy matters.",
        "tags": ["cafes", "food", "energetic", "loud"]
    }
]

PERSONA_HINTS = {
    "remote worker": "Lifestyle anchors weighted 3x. Coworking spaces surfaced. Commute tradeoffs softened.",
    "young family": "School quality and safety get extra weight. Kid-friendly parks and pet policies are prioritized.",
    "career relocator": "Commute, parking, and employer flexibility are surfaced with clear cost tradeoffs.",
    "empty nester": "Quiet streets, low-maintenance living, and pedestrian comfort are prioritized.",
}

PERSONA_STYLES = {
    "remote worker": {"score_bias": {"coffee-heavy": 3, "walkable": 2}, "checklist": ["Look for coworking spaces or coffee-shop stability."]},
    "young family": {"score_bias": {"quiet": 3, "dog-friendly": 2, "school-friendly": 3}, "checklist": ["Verify school zone ratings and nearby park access."]},
    "career relocator": {"score_bias": {"transit-access": 3, "parking": 3}, "checklist": ["Confirm parking policy and weekday commute time."]},
    "empty nester": {"score_bias": {"quiet": 4, "walkable": 2}, "checklist": ["Check unit maintenance, elevator access, and one-level living."]},
}

IMAGE_URLS = [
    "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1501183638710-841dd1904471?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=900&q=80",
]


def parse_profile(answers: OnboardingAnswers) -> UserProfile:
    city = answers.destination.split(",")[0].strip().title() or "Chicago"
    lifestyle = [x.strip().lower() for x in re.split(r",|and|;", answers.lifestyle) if x.strip()]
    dealbreakers = [x.strip().lower() for x in re.split(r",|and|;", answers.dealbreakers) if x.strip()]
    persona = answers.profile_type.strip().lower() if answers.profile_type else "remote worker"
    if persona not in PERSONA_HINTS:
        persona = "remote worker"
    return UserProfile(
        profile_type=persona,
        destination_city=city,
        monthly_budget=answers.budget,
        move_timeline=answers.move_timeline,
        work_style=answers.work_style,
        pets=answers.pets,
        lifestyle_priorities=lifestyle or ["walkability", "coffee shops"],
        dealbreakers=dealbreakers or ["noise"],
    )

def get_neighborhoods(profile: UserProfile):
    key = profile.destination_city.lower()
    base = NEIGHBORHOOD_LIBRARY.get(key, DEFAULT_NEIGHBORHOODS)
    adjusted = []
    persona_bias = PERSONA_STYLES.get(profile.profile_type, {}).get("score_bias", {})
    for n in base:
        score = n["score"]
        text = " ".join(profile.lifestyle_priorities + profile.dealbreakers + [profile.pets, profile.work_style]).lower()
        if "quiet" in text or "noise" in text:
            if "quiet" in n["tags"]:
                score += 4
            if "lively-weekends" in n["tags"] or "loud" in n["tags"]:
                score -= 3
        if "dog" in text and "dog-friendly" in n["tags"]:
            score += 3
        if "coffee" in text and ("coffee-heavy" in n["tags"] or "coffee" in n["tags"]):
            score += 3
        for tag, bias in persona_bias.items():
            if tag in n["tags"]:
                score += bias
        clone = dict(n)
        clone["score"] = max(1, min(100, score))
        clone["justification"] = (
            f"Matched against your budget of ${profile.monthly_budget:,}, your {profile.work_style} work style, pets: {profile.pets}, "
            f"and your preference for {', '.join(profile.lifestyle_priorities[:3])}."
        )
        clone["vibe_highlight"] = PERSONA_HINTS.get(profile.profile_type)
        adjusted.append(clone)
    return sorted(adjusted, key=lambda x: x["score"], reverse=True)

def build_listings(profile: UserProfile, neighborhoods: List[Dict[str, Any]]):
    rents = [profile.monthly_budget - 150, profile.monthly_budget - 50, profile.monthly_budget + 120]
    names = ["Sunlit 1BR near cafes", "Pet-friendly studio with workspace", "Quiet top-floor apartment"]
    listings = []
    sample_images = IMAGE_URLS
    for idx, name in enumerate(names):
        n = neighborhoods[idx % len(neighborhoods)]
        red_flags = []
        if rents[idx] > profile.monthly_budget:
            red_flags.append("Above stated budget after fees")
        if idx == 1:
            red_flags.append("Pet fee not clearly disclosed")
        if idx == 2:
            red_flags.append("Only 3 photos shown")
        rent = max(900, rents[idx])
        utilities = 140 if "studio" not in name.lower() else 110
        pet_fee = 50 if "dog" in profile.pets.lower() or "cat" in profile.pets.lower() or "pet" in profile.pets.lower() else 0
        true_cost = rent + utilities + pet_fee + 18
        listings.append({
            "id": f"apt-{idx+1}", "title": name, "neighborhood": n["name"], "rent": rent,
            "true_monthly_cost": true_cost, "cost_breakdown": {"rent": rent, "utilities": utilities, "pet_fee": pet_fee, "insurance": 18},
            "fit_score": max(60, n["score"] - idx * 4), "red_flags": red_flags,
            "image_url": sample_images[idx],
            "outreach": f"Hi, I’m interested in your {name.lower()} in {n['name']}. I’m moving {profile.move_timeline}, have a budget around ${profile.monthly_budget:,}, and wanted to confirm total monthly cost, pet policy, deposit terms, and availability for a video tour. Thanks!"
        })
    return listings

def build_checklist(profile: UserProfile):
    pet_task = [{"when": "2 weeks before", "title": "Confirm pet policy in writing", "detail": "Ask about breed restrictions, deposits, monthly pet rent, and nearby relief areas.", "link": "https://www.example.com/pet-policy"}] if any(x in profile.pets.lower() for x in ["dog", "cat", "pet"]) else []
    persona_links = PERSONA_STYLES.get(profile.profile_type, {}).get("checklist", [])
    return [
        {"when": "6 weeks before", "title": "Finalize target neighborhoods", "detail": "Shortlist 2-3 areas and compare fit, rent, commute, and noise.", "link": "https://www.google.com/maps"},
        {"when": "4 weeks before", "title": "Contact landlords", "detail": "Ask for total monthly cost, walkthrough, lease terms, and red flags.", "link": "mailto:leasing@example.com"},
        *pet_task,
        {"when": "2 weeks before", "title": "Book movers or shipping", "detail": "Get quotes, check reviews, and confirm insurance coverage.", "link": "https://www.moving.com"},
        {"when": "1 week before", "title": "Set up utilities and internet", "detail": "Schedule activation before move-in day if possible.", "link": "https://www.techradar.com/news/best-internet-provider"},
        {"when": "Move week", "title": "Do final walkthrough", "detail": "Record a video, test appliances, document damage, and collect keys.", "link": "https://www.example.com/walkthrough-checklist"},
        {"when": "After move", "title": "Update address", "detail": "Update bank, employer, subscriptions, IDs, and mail forwarding.", "link": "https://www.usps.com"},
        *([{"when": "Ongoing", "title": "Persona-specific advice", "detail": advice, "link": "https://www.example.com/advice"} for advice in persona_links]),
    ]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/onboarding/questions")
def onboarding_questions():
    return {"questions": QUESTIONS}

@app.post("/api/profile")
def create_profile(answers: OnboardingAnswers):
    profile = parse_profile(answers)
    neighborhoods = get_neighborhoods(profile)
    data = {
        "profile": profile.model_dump(),
        "neighborhoods": neighborhoods,
        "listings": build_listings(profile, neighborhoods),
        "checklist": build_checklist(profile),
    }
    SESSIONS[profile.session_id] = data
    return {"session_id": profile.session_id, "profile": profile.model_dump()}

@app.get("/api/profile/{session_id}")
def get_profile(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    return SESSIONS[session_id]["profile"]

async def sse_event(event: str, data: Dict[str, Any]):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

@app.get("/api/orchestrate/{session_id}")
async def orchestrate(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    session = SESSIONS[session_id]

    async def stream():
        agents = [
            ("profile_parser", "Profile Parser Agent", ["Reading your move story", "Extracting constraints", "Profile structured"]),
            ("neighborhood_fit", "Neighborhood Fit Agent", ["Comparing neighborhoods", "Weighting lifestyle priorities", "Fit scores ready"]),
            ("vibe_analyst", "Vibe Analyst Agent", ["Synthesizing local feel", "Checking quiet vs energy", "Vibe cards ready"]),
            ("apartment_scout", "Apartment Scout Agent", ["Scanning demo listings", "Checking red flags", "Apartment shortlist ready"]),
            ("checklist", "Moving Checklist Agent", ["Sequencing move tasks", "Adding pet and timeline tasks", "Checklist ready"]),
        ]
        yield await sse_event("start", {"agents": [{"id": a[0], "name": a[1]} for a in agents]})
        async def run_agent(agent_id, name, statuses, delay):
            for i, status in enumerate(statuses):
                await asyncio.sleep(delay + i * 0.45)
                yield await sse_event("agent_status", {"agent_id": agent_id, "name": name, "status": status, "progress": int(((i+1)/len(statuses))*100)})
            yield await sse_event("agent_done", {"agent_id": agent_id, "name": name})
        # Sequential streaming with stagger, visually enough for demo and reliable in browsers.
        for idx, agent in enumerate(agents):
            async for msg in run_agent(*agent, delay=0.25):
                yield msg
        yield await sse_event("results", {"results": session})
        yield await sse_event("complete", {"message": "All agents complete"})
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/api/results/{session_id}")
def results(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    return SESSIONS[session_id]

@app.post("/api/chat/{session_id}")
def chat(session_id: str, req: ChatRequest):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    data = SESSIONS[session_id]
    msg = req.message.lower()
    neighborhoods = data["neighborhoods"]
    chosen = None
    for n in neighborhoods:
        if n["name"].lower() in msg:
            chosen = n
            break
    if chosen is None:
        chosen = neighborhoods[0]
    if "safe" in msg or "night" in msg:
        answer = f"For your profile, I would treat {chosen['name']} as a good fit with one caution: {chosen['watchout']} The safer move is to tour during the evening, check lighting around the exact block, and avoid signing based only on the neighborhood name."
    elif "best" in msg or "choose" in msg:
        answer = f"I would start with {neighborhoods[0]['name']}. It has the highest fit score because it best matches your lifestyle priorities and dealbreakers. My second choice would be {neighborhoods[1]['name']} if you want a calmer trade-off."
    elif "email" in msg or "landlord" in msg:
        answer = data["listings"][0]["outreach"]
    else:
        answer = f"Based on your profile, {chosen['name']} is a {chosen['score']}/100 fit. The main upside is {', '.join(chosen['pros'][:2])}. The main trade-off is {chosen['watchout']}"
    return {"answer": answer}
