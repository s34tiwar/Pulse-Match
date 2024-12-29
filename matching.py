import numpy as np
from pulsedb import updateMatch, getUnmatchedIDs, getScores

# Function to calculate a compatibility percentage
def calculate_match_percentage(score):
   
    max_possible_score = 10  # Adjust this based on your scoring system.
    percentage = (score / max_possible_score) * 100
    return percentage

# Function to determine if it's a match based on a threshold
def is_match(percentage, threshold=50):
    """
    Default threshold is 50%.
    """
    return 1 if percentage >= threshold else 0

# Main matching algorithm
def perform_matching():
    """
    Perform the matching process:
    1. Fetch IDs and scores from the database.

    """
    # Fetch unmatched IDs
    ids = getUnmatchedIDs()

    # Error handling
    if ids is None or len(ids) == 0:
        print("Error: No IDs retrieved from the database.")
        return

    results = []  # Store match results

    for user_id in ids:
        # Fetch scores for the given user ID
        scores = getScores(user_id)

        if not scores or len(scores[0]) < 3:
            print(f"Error: No valid scores for user ID {user_id}. Skipping.")
            continue

        total_score = scores[0][2]  # Extract total score

        # Calculate match percentage
        match_percentage = calculate_match_percentage(total_score)

        # Determine if it's a match
        match_result = is_match(match_percentage)

        # Append results
        results.append((user_id, match_percentage, match_result))

        # Insert result back into the database
        updateMatch(match_percentage,user_id)

    print("Matching process completed.")
    return results  # return results for debugging or testing

# Execute matching algorithm
if __name__ == "__main__":
    perform_matching()
