"""
Extended Evaluation Scenarios for the Crime Scene Domain.

Includes 10 turns each for: Negation, 1-Hop, 2-Hop, 3-Hop, 4-Hop, and Belief Maintenance.
"""

# =====================================================================
# 1. NEGATION SET (10 Turns)
# Target: Negative phrasing while retrieving the correct factual state.
# =====================================================================
CRIME_NEGATION_TURNS = [
    {
        "attributes": ["suspect_a.status"],
        "beliefs": {},
        "question": "Is it false that Suspect A is a prime_suspect?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "B" # They are a prime_suspect, so saying it's false is 'False'.
    },
    {
        "attributes": ["case.theory"],
        "beliefs": {"officer_smith.status": "suspended"},
        # Smith suspended -> Admissible=none -> A status=cleared -> Theory=solo_perpetrator (B is still prime because B's alibi is confirmed when A is cleared)
        # Wait, if A is cleared, B's testimonial alibi = "confirmed". 
        # B's final alibi = "confirmed".
        # B status = "cleared". 
        # Theory = "unsolved"
        "question": "Is it inaccurate to declare the case theory as collusion?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "A" # Theory is unsolved. So Yes, saying collusion is inaccurate.
    },
    {
        "attributes": ["suspect_b.testimonial_alibi"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        # A evidence=none -> A status=cleared -> B testimonial=confirmed
        "question": "Is it untrue that Suspect B has a broken testimonial alibi?",
        "options": {"A": "True", "B": "False", "C": "Sometimes"},
        "correct": "A" # It's confirmed. So it's untrue it's broken.
    },
    {
        "attributes": ["case.lead_suspect"],
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt"},
        # Motive A = True. B motive = False. Theory=collusion. Lead -> suspect_a
        "question": "Is it not the case that Suspect B is the lead suspect?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A" # Lead is suspect_a. It is NOT the case that B is lead.
    },
    {
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"},
        # Digital alibi = confirmed -> final alibi = confirmed
        "question": "Is it false that Suspect B's final alibi is broken?",
        "options": {"A": "Yes", "B": "No", "C": "Cannot tell"},
        "correct": "A" # It's confirmed, so saying it's broken is false.
    },
    {
        "attributes": ["suspect_b.status"],
        "beliefs": {"suspect_b.alibi_partner": "suspect_c"},
        # A still prime. But B alibi partner != A -> testimonial = confirmed -> final = confirmed -> B status = cleared
        "question": "Is the assertion 'Suspect B is a prime_suspect' incorrect?",
        "options": {"A": "Yes", "B": "No", "C": "Maybe"},
        "correct": "A" # They are cleared.
    },
    {
        "attributes": ["case.theory"],
        "beliefs": {"suspect_b.alibi_partner": "suspect_c"},
        # A=prime, B=cleared -> Theory = solo_perpetrator
        "question": "Is it untrue that the case theory is unsolved?",
        "options": {"A": "True", "B": "False", "C": "None"},
        "correct": "A" # It is solo_perpetrator, so unsolved is untrue.
    },
    {
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {"suspect_a.financial_records": "debt"}, # Warrant is False
        # Motive verified = False (since no warrant)
        "question": "Is it false that Suspect A's motive is verified?",
        "options": {"A": "Yes", "B": "No", "C": "N/A"},
        "correct": "A" # Motive is False, so yes it's false it's verified.
    },
    {
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy"},
        # Theory=collusion. A motive=False. B motive=True. Lead -> suspect_b
        "question": "Is it incorrect to label 'both' as the lead suspect?",
        "options": {"A": "Yes", "B": "No", "C": "Sometimes"},
        "correct": "A" # It is suspect_b, so 'both' is incorrect.
    },
    {
        "attributes": ["suspect_a.admissible_evidence"],
        "beliefs": {"officer_smith.status": "suspended", "suspect_a.home_evidence": "knife"},
        # Suspended + logger=smith -> none.
        "question": "Is it untrue that the admissible evidence is a knife?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A" # It is none. So it's untrue.
    }
]

# =====================================================================
# 2. 1-HOP SET (10 Turns)
# Target: Direct derivations (Parent -> Child)
# =====================================================================
CRIME_1HOP_TURNS = [
    {
        "attributes": ["suspect_a.admissible_evidence"],
        "beliefs": {"officer_smith.status": "suspended"},
        "question": "If the arresting officer gets suspended, what happens to the admissible evidence logged by him?",
        "options": {"A": "none", "B": "gun", "C": "knife"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_a.status"],
        "beliefs": {"suspect_a.admissible_evidence": "none"},
        "question": "Without admissible evidence, what is Suspect A's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "unsolved"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_b.digital_alibi"],
        "beliefs": {"case.cctv_subject": "suspect_b", "case.cctv_status": "active"},
        "question": "With active CCTV showing Suspect B, what is the digital alibi?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"suspect_b.digital_alibi": "confirmed"},
        "question": "If the digital alibi is hard-confirmed, what is the final alibi?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_b.status"],
        "beliefs": {"suspect_b.final_alibi": "confirmed"},
        "question": "When the final alibi resolves to confirmed, what is Suspect B's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "charged"},
        "correct": "A"
    },
    {
        "attributes": ["case.theory"],
        "beliefs": {"suspect_a.status": "cleared"}, # B defaults to prime because B's alibi is broken? 
        # Wait, if A is cleared, B's testimonial = confirmed!
        # Ah, these direct beliefs inject at the middle layer. If we inject suspect_a.status="cleared", B's testimonial recalculates!
        # A="cleared" -> test="confirmed" -> final="confirmed" -> B="cleared".
        # So Theory="unsolved".
        "question": "If you override and forcefully clear Suspect A, what is the resulting case theory?",
        "options": {"A": "unsolved", "B": "solo_perpetrator", "C": "collusion"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt"},
        "question": "If a warrant is secured and they are in debt, is a motive verified?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_b.motive_verified"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy"},
        "question": "If they are known enemies, is Suspect B's motive verified?",
        "options": {"A": "True", "B": "False", "C": "Unsure"},
        "correct": "A"
    },
    {
        "attributes": ["case.lead_suspect"],
        "beliefs": {"case.theory": "solo_perpetrator", "suspect_b.status": "prime_suspect", "suspect_a.status": "cleared"},
        # Theory is solo, A is clear, B is prime.
        "question": "For a solo perpetrator theory where only B is prime, who is the lead?",
        "options": {"A": "suspect_b", "B": "suspect_a", "C": "both"},
        "correct": "A"
    },
    {
        "attributes": ["suspect_b.testimonial_alibi"],
        "beliefs": {"suspect_b.alibi_partner": "suspect_c"},
        "question": "If Suspect B claims Suspect C is their alibi, does it break?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    }
]

# =====================================================================
# 3. 2-HOP SET (10 Turns)
# Target: Two levels of indirection.
# =====================================================================
CRIME_2HOP_TURNS = [
    {   # Home Evid(1) -> Admiss(2) -> Status A
        "attributes": ["suspect_a.status"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        "question": "Without home evidence, what is Suspect A's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "unsolved"},
        "correct": "A"
    },
    {   # Officer(1) -> Admiss(2) -> Status A
        "attributes": ["suspect_a.status"],
        "beliefs": {"officer_smith.status": "suspended"},
        "question": "If Smith is suspended, what becomes of Suspect A?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "convicted"},
        "correct": "A"
    },
    {   # Status A(1) -> Testimonial B(2) -> Final Alibi B
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"suspect_a.status": "cleared"},
        "question": "If Suspect A is cleared, what is Suspect B's final alibi status?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {   # Partner(1) -> Testimonial B(2) -> Final Alibi B
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"suspect_b.alibi_partner": "wife"},
        "question": "If B changes their alibi partner to their wife, what is the final alibi?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {   # CCTV(1) -> Digital B(2) -> Final Alibi B
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"case.cctv_subject": "suspect_b", "case.cctv_status": "active"},
        "question": "With CCTV capturing Suspect B, what is their final alibi?",
        "options": {"A": "confirmed", "B": "broken", "C": "active"},
        "correct": "A"
    },
    {   # Final B(1) -> Status B(2) -> Theory
        "attributes": ["case.theory"],
        "beliefs": {"suspect_b.final_alibi": "confirmed"},
        # A is prime, B is cleared -> solo
        "question": "If B's final alibi is fully confirmed, what is the case theory?",
        "options": {"A": "solo_perpetrator", "B": "unsolved", "C": "collusion"},
        "correct": "A"
    },
    {   # Warrant(1) -> Motive A(2) -> Lead Suspect
        "attributes": ["case.lead_suspect"],
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt"},
        # Motive A verifies -> Lead = suspect_a
        "question": "With a warrant securing debt records, who becomes the ultimate lead in collusion?",
        "options": {"A": "suspect_a", "B": "both", "C": "suspect_b"},
        "correct": "A"
    },
    {   # Relation B(1) -> Motive B(2) -> Lead Suspect
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy"},
        # Motive B verifies -> Lead = suspect_b
        "question": "With B verified as an enemy, who is the lead for the collusion tie-breaker?",
        "options": {"A": "suspect_b", "B": "both", "C": "suspect_a"},
        "correct": "A"
    },
    {   # Status A(1) -> Theory(2) -> Lead Suspect
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_a.status": "cleared", "suspect_b.status": "prime_suspect"},
        # A clear, B prime -> solo -> suspect_b
        "question": "If A is cleared but B is somehow kept prime, who is the lead?",
        "options": {"A": "suspect_b", "B": "suspect_a", "C": "none"},
        "correct": "A"
    },
    {   # Status B(1) -> Theory(2) -> Lead Suspect
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.status": "cleared"},
        # A is prime, B clear -> solo -> suspect_a
        "question": "If B's status drops to cleared, who is the lead suspect?",
        "options": {"A": "suspect_a", "B": "both", "C": "suspect_b"},
        "correct": "A"
    }
]

# =====================================================================
# 4. 3-HOP SET (10 Turns)
# Target: Three levels of indirection.
# =====================================================================
CRIME_3HOP_TURNS = [
    {   # Officer(1) -> Admiss(2) -> Status A(3) -> Theory
        "attributes": ["case.theory"],
        "beliefs": {"officer_smith.status": "suspended"},
        # A cleared. B testimonial confirmed -> B final confirmed -> B cleared. Theory = unsolved.
        "question": "Smith is suspended. What is the overall case theory?",
        "options": {"A": "unsolved", "B": "solo_perpetrator", "C": "collusion"},
        "correct": "A"
    },
    {   # Partner(1) -> Testimonial(2) -> Final(3) -> Status B
        "attributes": ["suspect_b.status"],
        "beliefs": {"suspect_b.alibi_partner": "mom"},
        # B cleared
        "question": "Suspect B brings in their mom as an alibi. What is B's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "jailed"},
        "correct": "A"
    },
    {   # CCTV(1) -> Digital(2) -> Final(3) -> Status B
        "attributes": ["suspect_b.status"],
        "beliefs": {"case.cctv_subject": "suspect_b", "case.cctv_status": "active"},
        # B cleared
        "question": "If CCTV cleanly catches Suspect B, what is B's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "unsolved"},
        "correct": "A"
    },
    {   # Status A(1) -> Testimonial(2) -> Final(3) -> Status B
        "attributes": ["suspect_b.status"],
        "beliefs": {"suspect_a.status": "cleared"},
        # A clear -> test confirm -> B clear
        "question": "If A is cleared manually, what happens to B's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "both"},
        "correct": "A"
    },
    {   # Final B(1) -> Status B(2) -> Theory(3) -> Lead
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.final_alibi": "confirmed"},
        # B cleared. A is prime. Theory solo -> Lead = A
        "question": "Given B's final alibi is confirmed, who is the lead suspect?",
        "options": {"A": "suspect_a", "B": "suspect_b", "C": "none"},
        "correct": "A"
    },
    {   # HomeEvid(1) -> Admiss(2) -> Status A(3) -> Testimonial B
        "attributes": ["suspect_b.testimonial_alibi"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        # A clear -> Test = confirmed
        "question": "If the gun vanishes from A's home, what is B's testimonial alibi?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {   # Status A(1) -> Theory(2) -> Lead(3)    (Actually Status A(1)->Test(2)->Final(3)->SB(4)->Theory...)
        # Let's do: B.Status(1) -> Theory(2) -> Lead(3)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.status": "cleared"},
        # A prime -> solo -> A
        "question": "If Suspect B is cleared of all charges, who leads the solo theory?",
        "options": {"A": "suspect_a", "B": "suspect_b", "C": "none"},
        "correct": "A"
    },
    {   # Warrant(1) -> Motive A(2) -> Lead(3) ... Wait, Lead is 1 hop from Motive.
        # How about: Officer(1) -> Admiss(2) -> Status A(3) -> Theory(4) -> Lead(5)
        # We will put that in 4-HOP and 5-HOP.
        # For 3-hop: HomeEvid(1) -> Admiss(2) -> Status A(3) -> Theory
        "attributes": ["case.theory"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        # A clear, B test confirmed -> B final confirmed -> B clear. Theory = unsolved
        "question": "Without home evidence for A, what is the case theory?",
        "options": {"A": "unsolved", "B": "solo_perpetrator", "C": "collusion"},
        "correct": "A"
    },
    {   # Relation(1) -> Motive B(2) -> Lead(3)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy", "suspect_a.motive_verified": False},
        "question": "If B is an enemy and A has no motive, who leads the case?",
        "options": {"A": "suspect_b", "B": "suspect_a", "C": "both"},
        "correct": "A"
    },
    {   # CCTV(1) -> Digital(2) -> Final(3) -> Status B
        "attributes": ["suspect_b.status"],
        "beliefs": {"case.cctv_status": "corrupted", "suspect_b.alibi_partner": "suspect_c"},
        # No digital, but test confirmed -> B clear
        "question": "With corrupted CCTV but a new alibi partner, what is B's status?",
        "options": {"A": "cleared", "B": "prime_suspect", "C": "guilty"},
        "correct": "A"
    }
]

# =====================================================================
# 5. 4-HOP SET (10 Turns)
# Target: 4+ levels of indirection. Deepest possible logic tracing.
# =====================================================================
CRIME_4HOP_TURNS = [
    {   # Officer(1) -> Admiss(2) -> Status A(3) -> Testimonial B(4) -> Final B(5)
        "attributes": ["suspect_b.final_alibi"],
        "beliefs": {"officer_smith.status": "suspended"},
        # A cleared -> Test B=confirmed -> Final B=confirmed
        "question": "Officer Smith gets suspended. What is Suspect B's final alibi outcome?",
        "options": {"A": "confirmed", "B": "broken", "C": "none"},
        "correct": "A"
    },
    {   # HomeEvid(1) -> Admiss(2) -> Status A(3) -> Testimonial B(4) -> Status B(5) -> Theory(6)
        "attributes": ["case.theory"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        # A clear -> test confirm -> B clear -> unsolved
        "question": "The gun at A's house is ruled inadmissible. What is the case theory?",
        "options": {"A": "unsolved", "B": "collusion", "C": "solo_perpetrator"},
        "correct": "A"
    },
    {   # Same as above, retrieving Lead Suspect (hop 7)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_a.home_evidence": "none"},
        # Unsolved -> none
        "question": "With A's home evidence cleared, who is the lead suspect?",
        "options": {"A": "none", "B": "suspect_a", "C": "suspect_b"},
        "correct": "A"
    },
    {   # Partner(1) -> Test B(2) -> Final B(3) -> Status B(4) -> Theory(5)
        "attributes": ["case.theory"],
        "beliefs": {"suspect_b.alibi_partner": "wife"},
        # B clear -> A prime -> solo
        "question": "If B brings their wife as an alibi, what happens to the theory?",
        "options": {"A": "solo_perpetrator", "B": "collusion", "C": "unsolved"},
        "correct": "A"
    },
    {   # Partner(1) -> Test B(2) -> Final B(3) -> Status B(4) -> Lead(5)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_b.alibi_partner": "mom"},
        # B clear -> A prime -> solo -> lead=A
        "question": "B's mom alibis him. Who is the lead suspect?",
        "options": {"A": "suspect_a", "B": "suspect_b", "C": "none"},
        "correct": "A"
    },
    {   # CCTV(1) -> Digital B(2) -> Final B(3) -> Status B(4) -> Theory(5)
        "attributes": ["case.theory"],
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"},
        # Digital confirm -> B clear -> solo A
        "question": "CCTV clears B. What is the new theory?",
        "options": {"A": "solo_perpetrator", "B": "unsolved", "C": "collusion"},
        "correct": "A"
    },
    {   # CCTV(1) -> Digital B(2) -> Final B(3) -> Status B(4) -> Lead(5)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"},
        # Lead A
        "question": "CCTV confirms B was miles away. Who is the lead?",
        "options": {"A": "suspect_a", "B": "suspect_b", "C": "both"},
        "correct": "A"
    },
    {   # Officer(1) -> Admiss(2) -> Status A(3) -> Theory(4) -> Lead(5)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"officer_smith.status": "suspended"},
        # A clear -> B clear -> unsolved -> none
        "question": "Smith is suspended. Who is the lead suspect?",
        "options": {"A": "none", "B": "suspect_a", "C": "both"},
        "correct": "A"
    },
    {   # Logger(1) -> Admiss(2) -> Status A(3) -> Test B(4) -> B Status(5)
        "attributes": ["suspect_b.status"],
        "beliefs": {"suspect_a.evidence_logger": "admin", "officer_smith.status": "suspended"},
        # Admiss = gun (since logger != smith). A=prime. Test B=broken. B=prime
        "question": "If an admin logged A's evidence instead of suspended Smith, what is B's status?",
        "options": {"A": "prime_suspect", "B": "cleared", "C": "unknown"},
        "correct": "A"
    },
    {   # Logger(1) -> Admiss(2) -> Status A(3) -> Theory(4) -> Lead(5)
        "attributes": ["case.lead_suspect"],
        "beliefs": {"suspect_a.evidence_logger": "admin", "officer_smith.status": "suspended", "suspect_a.financial_records": "debt", "case.warrant_status": True},
        # Collusion. Motive A matches. Lead = suspect_a
        "question": "Admin logs evidence. Warrant secures A's debt. Who is lead among the collusion?",
        "options": {"A": "suspect_a", "B": "suspect_b", "C": "both"},
        "correct": "A"
    }
]

# =====================================================================
# 6. BELIEF MAINTENANCE SET (10 Turns)
# Target: Adding unrelated input beliefs should NOT affect independently-derived attributes.
# Tests that different dependency chains are orthogonal.
# =====================================================================
CRIME_BELIEF_MAINTENANCE_TURNS = [
    {   # Query: suspect_a.status with just home evidence
        "attributes": ["suspect_a.status"],
        "beliefs": {"suspect_a.home_evidence": "knife"},
        "question": "With a knife found at A's home, what is A's status?",
        "options": {"A": "prime_suspect", "B": "cleared", "C": "unknown"},
        "correct": "A"  # Home evidence present -> admissible -> prime_suspect
    },
    {   # Add unrelated warrant status (affects motive, not status) -> A status same
        "attributes": ["suspect_a.status"],
        "beliefs": {"suspect_a.home_evidence": "knife", "case.warrant_status": True},
        "question": "After securing a warrant, is A still a prime suspect?",
        "options": {"A": "prime_suspect", "B": "cleared", "C": "changed"},
        "correct": "A"  # Maintained: status depends on evidence only, not warrant
    },
    {   # Query: suspect_b.motive_verified with just relation
        "attributes": ["suspect_b.motive_verified"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy"},
        "question": "If B is an enemy of the victim, is motive verified?",
        "options": {"A": "True", "B": "False", "C": "Pending"},
        "correct": "A"  # B relation -> motive verified
    },
    {   # Add unrelated evidence chain (affects A, not B motive) -> B motive same
        "attributes": ["suspect_b.motive_verified"],
        "beliefs": {"suspect_b.relation_to_victim": "enemy", "suspect_a.home_evidence": "gun"},
        "question": "Adding evidence about A, is B's motive still verified?",
        "options": {"A": "True", "B": "False", "C": "Unclear"},
        "correct": "A"  # Maintained: B motive depends on relation only
    },
    {   # Query: suspect_a.motive_verified with warrant + financial records
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt"},
        "question": "With warrant and debt records, is A's motive verified?",
        "options": {"A": "True", "B": "False", "C": "Unclear"},
        "correct": "A"  # Warrant + debt -> motive verified
    },
    {   # Add unrelated alibi witness (affects B, not A motive) -> A motive same
        "attributes": ["suspect_a.motive_verified"],
        "beliefs": {"case.warrant_status": True, "suspect_a.financial_records": "debt", "suspect_b.alibi_partner": "sister"},
        "question": "After B provides an alibi witness, is A's motive still verified?",
        "options": {"A": "True", "B": "False", "C": "Changed"},
        "correct": "A"  # Maintained: A motive depends on warrant + records only
    },
    {   # Query: suspect_b.digital_alibi with CCTV chain
        "attributes": ["suspect_b.digital_alibi"],
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b"},
        "question": "With CCTV recording B, is digital alibi confirmed?",
        "options": {"A": "confirmed", "B": "none", "C": "broken"},
        "correct": "A"  # Digital CCTV confirms alibi
    },
    {   # Add unrelated home evidence (affects A status, not B digital) -> B digital same
        "attributes": ["suspect_b.digital_alibi"],
        "beliefs": {"case.cctv_status": "active", "case.cctv_subject": "suspect_b", "suspect_a.home_evidence": "none"},
        "question": "When A's home evidence disappears, is B's digital alibi still confirmed?",
        "options": {"A": "confirmed", "B": "none", "C": "compromised"},
        "correct": "A"  # Maintained: digital depends on CCTV only
    },
    {   # Query: case.theory with both statuses (A prime, B cleared)
        "attributes": ["case.theory"],
        "beliefs": {"suspect_a.status": "prime_suspect", "suspect_b.status": "cleared"},
        "question": "With A prime and B cleared, what is the case theory?",
        "options": {"A": "solo_perpetrator", "B": "collusion", "C": "unsolved"},
        "correct": "A"  # One prime -> solo_perpetrator
    },
    {   # Add unrelated motive facts (B relation) -> theory still solo
        "attributes": ["case.theory"],
        "beliefs": {"suspect_a.status": "prime_suspect", "suspect_b.status": "cleared", "suspect_b.relation_to_victim": "friend"},
        "question": "After learning B is friends with victim, is theory still solo?",
        "options": {"A": "solo_perpetrator", "B": "collusion", "C": "changed"},
        "correct": "A"  # Maintained: theory depends on statuses only, not motives
    }
]
