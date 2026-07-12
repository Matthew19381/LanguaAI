"""
Neuro-Informed FSRS V2
Extends standard FSRS with neuroscience parameters for optimal language learning.
"""

import math
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone, timedelta


@dataclass
class NeuroFSRSParams:
    # Standard FSRS parameters (optimized for language learning)
    w: list = (
        0.4, 0.6, 2.4, 5.8, 4.9, 0.9, 0.6, 0.0, 1.5, 0.1, 1.0, 1.0, 0.0
    )
    # Neuro extensions
    sleep_modulator_weight: float = 0.15      # 0-0.3
    time_of_day_weight: float = 0.1           # 0-0.2
    interleaving_bonus_weight: float = 0.05   # 0-0.1
    interference_penalty_weight: float = 0.1  # 0-0.2


@dataclass
class NeuroCardState:
    difficulty: float
    stability: float
    retrievability: float
    interval_days: int
    repetitions: int
    lapses: int = 0
    # Neuro fields
    sleep_quality: Optional[int] = None       # 1-5
    session_type: str = "day"                 # "evening" | "morning" | "day"
    interleaving_bonus: float = 0.0           # 0-1
    interference_penalty: float = 0.0         # 0-1
    time_of_day: str = "day"                  # "morning" | "day" | "evening"
    state: str = "Learning"                   # "Learning", "Review", "Relearning"


def calculate_sleep_modulator(sleep_quality: int, session_type: str) -> float:
    """Sleep modulates consolidation"""
    if sleep_quality is None:
        sleep_quality = 3  # neutral
    
    base = sleep_quality / 5.0  # 0.2 - 1.0
    
    if session_type == "evening":
        # Evening encoding boost (consolidation during sleep)
        return 1.0 + 0.2 * (base - 0.5)  # 0.9 - 1.1
    elif session_type == "morning":
        # Morning retrieval boost (after sleep consolidation)
        return 1.0 + 0.25 * (base - 0.5)  # 0.875 - 1.125
    return 1.0 + 0.15 * (base - 0.5)  # 0.925 - 1.075


def neuro_fsrs_params_from_user(user) -> "NeuroFSRSParams":
    """Build NeuroFSRSParams using the user's configurable weights (NEURO-15).

    Reads the JSON ``neuro_weights`` column on the User model. Falls back to the
    dataclass defaults if the column is missing or invalid.
    """
    defaults = NeuroFSRSParams()
    raw = getattr(user, "neuro_weights", None)
    if not raw:
        return defaults
    try:
        import json
        weights = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return defaults

    return NeuroFSRSParams(
        sleep_modulator_weight=float(weights.get(
            "sleep_modulator_weight", defaults.sleep_modulator_weight)),
        time_of_day_weight=float(weights.get(
            "time_of_day_weight", defaults.time_of_day_weight)),
        interleaving_bonus_weight=float(weights.get(
            "interleaving_bonus_weight", defaults.interleaving_bonus_weight)),
        interference_penalty_weight=float(weights.get(
            "interference_penalty_weight", defaults.interference_penalty_weight)),
    )


def calculate_time_of_day_factor(session_type: str, current_hour: int) -> float:
    """Circadian rhythm modulation"""
    if session_type == "morning" and 6 <= current_hour <= 10:
        return 1.1  # peak cortisol/alertness
    elif session_type == "evening" and 20 <= current_hour <= 22:
        return 1.05  # pre-sleep consolidation window
    return 1.0


def calculate_interference_penalty(similar_cards_count: int, max_similar: int = 5) -> float:
    """Similar items create interference"""
    if similar_cards_count <= 1:
        return 0.0
    return min(0.3, (similar_cards_count - 1) / max_similar * 0.3)


def neuro_fsrs_next_interval(
    card: NeuroCardState,
    rating: int,  # 1=Again, 2=Hard, 3=Good, 4=Easy
    params: NeuroFSRSParams = NeuroFSRSParams(),
    similar_count: int = 0,
    current_hour: int = 12
) -> NeuroCardState:
    """Returns updated card state with neuro modulation"""
    
    # Standard FSRS calculation (simplified version)
    # In production, use the full FSRS implementation from fsrs3 library
    w = params.w
    
    # Map rating to FSRS parameters
    if rating == 1:  # Again
        d = w[0]  # difficulty increase
        s = w[1]  # stability decrease
    elif rating == 2:  # Hard
        d = w[2]
        s = w[3]
    elif rating == 3:  # Good
        d = w[4]
        s = w[5]
    else:  # Easy (rating == 4)
        d = w[6]
        s = w[7]
    
    # Calculate new difficulty and stability
    new_difficulty = card.difficulty + d - (w[8] * card.difficulty)
    new_difficulty = max(0.1, min(10.0, new_difficulty))
    
    # Stability calculation (simplified)
    if card.stability == 0:
        stability = w[9] * math.exp(w[10] * card.difficulty)
    else:
        stability = card.stability * math.exp(w[11] * (1 - card.difficulty / 10) * (pow(s, -w[12]) - 1))
    
    # Apply neuro modulation
    sleep_mod = calculate_sleep_modulator(card.sleep_quality or 3, card.session_type)
    tod_mod = calculate_time_of_day_factor(card.session_type, current_hour)
    interference = calculate_interference_penalty(similar_count)
    interleaving_bonus = card.interleaving_bonus
    
    # Combined modulator
    total_modulator = (
        (1 + (sleep_mod - 1) * params.sleep_modulator_weight) *
        (1 + (tod_mod - 1) * params.time_of_day_weight) *
        (1 - interference * params.interference_penalty_weight) *
        (1 + interleaving_bonus * params.interleaving_bonus_weight)
    )
    
    # Apply to stability
    new_stability = stability * total_modulator
    new_stability = max(0.1, new_stability)
    
    # Calculate retrievability and interval
    # Simple approximation: R = e^(-t/S) where t=1 day, S=stability
    days = 1.0
    retrievability = math.exp(-days / new_stability)
    
    # Calculate next interval (simplified)
    if retrievability >= 0.9:
        interval_days = max(1, int(new_stability * (rating - 1)))
    elif retrievability >= 0.85:
        interval_days = max(1, int(new_stability * 0.5))
    else:
        interval_days = 1  # relearn
    
    # Update repetitions and lapses
    new_repetitions = card.repetitions + (1 if rating >= 3 else 0)
    new_lapses = card.lapses + (1 if rating == 1 else 0)
    
    # Determine new state
    if rating == 1:  # Again
        new_state = "Relearning"
    else:
        if card.repetitions == 0:
            new_state = "Learning"
        else:
            new_state = "Review"
    
    return NeuroCardState(
        difficulty=new_difficulty,
        stability=new_stability,
        retrievability=retrievability,
        interval_days=max(1, interval_days),
        repetitions=new_repetitions,
        lapses=new_lapses,
        sleep_quality=card.sleep_quality,
        session_type=card.session_type,
        interleaving_bonus=card.interleaving_bonus,
        interference_penalty=interference,
        time_of_day=("morning" if 6 <= current_hour <= 11 else 
                    "evening" if 18 <= current_hour <= 22 else 
                    "day"),
        state=new_state
    )