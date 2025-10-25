#!/usr/bin/env python3
"""
APEX v3.0 Lead Scoring Test Script
Tests Priority 1 fixes to enhanced_crm_agent.py
"""
import sys
sys.path.insert(0, '/app')

from app.agents.enhanced_crm_agent import EnhancedCRMAgent

def test_lead_scoring():
    """Test the BMW X3 scenario that was failing before."""

    print("=" * 80)
    print("APEX v3.0 LEAD SCORING TEST")
    print("=" * 80)
    print()

    # Initialize agent
    agent = EnhancedCRMAgent()

    # Test Case 1: BMW X3 with price inquiry and website reference (should be HOT)
    test_message_1 = "Ik zag de BMW X3 op jullie website. Wat kost deze?"

    print("TEST 1: BMW X3 Specifieke Vraag (Priority Scenario)")
    print("-" * 80)
    print(f"Message: {test_message_1}")
    print()

    result_1 = agent.calculate_score(test_message_1)

    print(f"Total Score: {result_1['score']}")
    print(f"Lead Quality: {result_1['quality']}")
    print()
    print("Score Breakdown:")
    for category, points in result_1['breakdown'].items():
        if points > 0:
            print(f"  - {category}: {points} points")
    print()

    # Expected: 70+ points (HOT)
    # - BMW X3 (specific model): +25
    # - "wat kost" (price inquiry): +25
    # - "website" (website reference): +20
    # = 70 points minimum

    expected_score_min = 70
    expected_quality = "HOT"

    if result_1['score'] >= expected_score_min and result_1['quality'] == expected_quality:
        print(f"✅ TEST 1 PASSED: Score {result_1['score']} >= {expected_score_min}, Quality = {expected_quality}")
    else:
        print(f"❌ TEST 1 FAILED: Expected {expected_quality} ({expected_score_min}+), got {result_1['quality']} ({result_1['score']})")

    print()
    print("=" * 80)
    print()

    # Test Case 2: Financiering vraag (should be HOT)
    test_message_2 = "Hoe zit het met financiering?"

    print("TEST 2: Financiering Vraag")
    print("-" * 80)
    print(f"Message: {test_message_2}")
    print()

    result_2 = agent.calculate_score(test_message_2)

    print(f"Total Score: {result_2['score']}")
    print(f"Lead Quality: {result_2['quality']}")
    print()
    print("Score Breakdown:")
    for category, points in result_2['breakdown'].items():
        if points > 0:
            print(f"  - {category}: {points} points")
    print()

    # Expected: Should score as HOT or WARM
    if result_2['quality'] in ["HOT", "WARM"]:
        print(f"✅ TEST 2 PASSED: Quality = {result_2['quality']} (acceptable)")
    else:
        print(f"⚠️  TEST 2 WARNING: Got {result_2['quality']}, expected HOT or WARM")

    print()
    print("=" * 80)
    print()

    # Test Case 3: Budget mention (should be WARM)
    test_message_3 = "Ik zoek een auto rond €25.000. Wat hebben jullie?"

    print("TEST 3: Budget €25K (WARM Lead)")
    print("-" * 80)
    print(f"Message: {test_message_3}")
    print()

    result_3 = agent.calculate_score(test_message_3)

    print(f"Total Score: {result_3['score']}")
    print(f"Lead Quality: {result_3['quality']}")
    print()
    print("Score Breakdown:")
    for category, points in result_3['breakdown'].items():
        if points > 0:
            print(f"  - {category}: {points} points")
    print()

    # Expected: WARM (40-74 points)
    if result_3['quality'] == "WARM":
        print(f"✅ TEST 3 PASSED: Quality = WARM")
    else:
        print(f"⚠️  TEST 3: Got {result_3['quality']}, expected WARM")

    print()
    print("=" * 80)
    print()

    # Test Case 4: Generic inquiry (should be COLD)
    test_message_4 = "Hallo! Hebben jullie occasions?"

    print("TEST 4: Generic Vraag (COLD Lead)")
    print("-" * 80)
    print(f"Message: {test_message_4}")
    print()

    result_4 = agent.calculate_score(test_message_4)

    print(f"Total Score: {result_4['score']}")
    print(f"Lead Quality: {result_4['quality']}")
    print()
    print("Score Breakdown:")
    for category, points in result_4['breakdown'].items():
        if points > 0:
            print(f"  - {category}: {points} points")
    print()

    # Expected: COLD (0-39 points)
    if result_4['quality'] == "COLD":
        print(f"✅ TEST 4 PASSED: Quality = COLD")
    else:
        print(f"⚠️  TEST 4: Got {result_4['quality']}, expected COLD")

    print()
    print("=" * 80)
    print()

    # Summary
    print("SUMMARY:")
    print("-" * 80)
    print(f"Test 1 (BMW X3): {result_1['quality']} ({result_1['score']} points)")
    print(f"Test 2 (Financiering): {result_2['quality']} ({result_2['score']} points)")
    print(f"Test 3 (Budget €25K): {result_3['quality']} ({result_3['score']} points)")
    print(f"Test 4 (Generic): {result_4['quality']} ({result_4['score']} points)")
    print()

    # Critical test: Test 1 must pass
    if result_1['score'] >= 70 and result_1['quality'] == "HOT":
        print("✅ APEX v3.0 PRIORITY 1 FIX: VALIDATED")
        print("   BMW X3 scenario now correctly scores as HOT lead")
        return 0
    else:
        print("❌ APEX v3.0 PRIORITY 1 FIX: FAILED")
        print(f"   BMW X3 scenario scored {result_1['score']} ({result_1['quality']}), expected 70+ (HOT)")
        return 1

if __name__ == "__main__":
    sys.exit(test_lead_scoring())
