"""Controlled content taxonomy for court videos."""
from __future__ import annotations

CATEGORIES = {
    "cop_misconduct": {
        "label": "Cop misconduct / civil rights",
        "patterns": [r"\bcops?\b", r"\bpolice\b", r"\bofficers?\b", r"\bdeputy\b", r"\bbody ?cam\b", r"\bqualified immunity\b", r"\bexcessive force\b", r"\bcivil rights\b", r"\btraffic stop\b", r"\bwrongful arrest\b"],
        "why": "Police conduct, bodycam evidence and civil-rights consequences are the strongest competitor category.",
    },
    "sovereign_citizen": {
        "label": "Sovereign citizen",
        "patterns": [r"\bsovereign citizen\b", r"\bstraw ?man\b", r"\bliving man\b", r"\bbeneficiary\b", r"\barticle\s+(?:4|IV)\b", r"\bcommon law\b", r"\bi know my rights\b", r"\bjurisdiction\b"],
        "why": "A self-represented defendant challenging the court's authority creates a clear power-reversal story.",
    },
    "dui": {
        "label": "DUI / drunk driving",
        "patterns": [r"\bDUI\b", r"\bDWI\b", r"\bdrunk driving\b", r"\bintoxicat", r"\bBAC\b", r"\bfield sobriety\b", r"\bbreathalyz"],
        "why": "DUI hearings give a concrete test, a number and a visible consequence.",
    },
    "domestic_violence": {
        "label": "Domestic / relationship",
        "patterns": [r"\bdomestic\b", r"\bstrangul", r"\brestraining order\b", r"\bspouse\b", r"\bhusband\b", r"\bwife\b", r"\bboyfriend\b", r"\bgirlfriend\b"],
        "why": "Relationship violence cases combine a clear victim story with high emotional stakes.",
    },
    "child_abuse": {
        "label": "Child abuse / children",
        "patterns": [r"\bchild abuse\b", r"\bchildren\b", r"\bchild\b", r"\btoddler\b", r"\bbaby\b", r"\bDCFS\b", r"\bCPS\b", r"\bminor\b", r"\bkids?\b"],
        "why": "Cases involving children produce strong protective outrage and clear sentencing stakes.",
    },
    "assault": {
        "label": "Assault / violence",
        "patterns": [r"\bassault\b", r"\bbattery\b", r"\bpunched\b", r"\battack(?:ed|ing)?\b", r"\bviolence\b", r"\bfight(?:ing)?\b"],
        "why": "A clear act of violence gives the clip a simple, visual conflict.",
    },
    "weapons": {
        "label": "Weapons",
        "patterns": [r"\bgun\b", r"\bfirearm\b", r"\bweapon\b", r"\bconcealed\b", r"\bammunition\b"],
        "why": "Weapons charges add seriousness and a tangible object for the thumbnail.",
    },
    "drugs": {
        "label": "Drugs",
        "patterns": [r"\bdrugs?\b", r"\bmeth\b", r"\bcocaine\b", r"\bfentanyl\b", r"\bheroin\b", r"\bmarijuana\b", r"\bTHC\b", r"\btrafficking\b"],
        "why": "Drug cases often combine addiction, probation and sentencing decisions.",
    },
    "theft_fraud": {
        "label": "Theft / fraud",
        "patterns": [r"\btheft\b", r"\bstole\b", r"\bfraud\b", r"\bshoplift", r"\bburglar", r"\bembezzl", r"\bscam\b"],
        "why": "Theft and fraud cases are easy to explain and often have a surprising paper trail.",
    },
    "probation": {
        "label": "Probation / parole",
        "patterns": [r"\bprobation\b", r"\bparole\b", r"\bviolation\b", r"\bcompliance\b", r"\btether\b"],
        "why": "A probation violation is a clear second-chance story with an immediate jail risk.",
    },
    "bond": {
        "label": "Bond / bail",
        "patterns": [r"\bbond\b", r"\bbail\b", r"\brelease\b"],
        "why": "Bond fights are fast, high-stakes and easy to follow.",
    },
    "sentencing": {
        "label": "Sentencing",
        "patterns": [r"\bsentenc", r"\byears?\b", r"\bprison\b", r"\bjail\b", r"\blocked up\b"],
        "why": "A specific sentence gives the audience a number to react to.",
    },
    "family_custody": {
        "label": "Family / custody",
        "patterns": [r"\bcustody\b", r"\bdivorce\b", r"\bchild support\b", r"\bvisitation\b", r"\bfamily court\b", r"\bannulment\b"],
        "why": "Family cases turn on identity, children and emotional testimony.",
    },
    "traffic": {
        "label": "Traffic / license",
        "patterns": [r"\btraffic\b", r"\blicense\b", r"\bspeeding\b", r"\bexpired tag\b", r"\bregistration\b", r"\bdriving while\b", r"\bplate\b"],
        "why": "Traffic stops are a familiar flashpoint for rights disputes.",
    },
    "mental_health": {
        "label": "Mental health",
        "patterns": [r"\bmental\b", r"\bschizophren", r"\bbipolar\b", r"\bpsych", r"\bcompetency\b"],
        "why": "Mental-health context adds a human explanation and raises the stakes.",
    },
}

TOPIC_ORDER = list(CATEGORIES.keys())

STAGE_PATTERNS = [
    ("sentencing", [r"\bsentenc", r"\bpunishment\b"]),
    ("plea", [r"\bplea\b", r"\bpleaded\b", r"\bguilty plea\b", r"\bno contest\b"]),
    ("bond", [r"\bbond\b", r"\bbail\b"]),
    ("trial", [r"\btrial\b", r"\bjury\b", r"\bverdict\b"]),
    ("arraignment", [r"\barraign", r"\bfirst appearance\b", r"\binitial appearance\b"]),
    ("appeal", [r"\bappeal\b", r"\bappellate\b"]),
    ("hearing", [r"\bhearing\b", r"\bdocket\b", r"\bmotion\b"]),
]

OUTCOME_PATTERNS = [
    ("sentenced", [r"\bsentenced to\s+([^.]{0,80})"]),
    ("bond set", [r"\bbond (?:is |was )?(?:set )?(?:at )?\$?([\d,]+)"]),
    ("guilty", [r"\bfound guilty\b", r"\bpleaded guilty\b", r"\bguilty plea\b"]),
    ("dismissed", [r"\bdismissed\b", r"\bcase dismissed\b"]),
    ("acquitted", [r"\bnot guilty\b", r"\bacquitted\b"]),
    ("probation", [r"\bprobation\b"]),
    ("jail", [r"\b(?:jail|prison)\b"]),
]
