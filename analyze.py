from openai import OpenAI
import os
from pydantic import BaseModel
from sklearn.preprocessing import MinMaxScaler
import numpy as np
import math

class Compatibility(BaseModel):
    affection: int
    vulnerability: int
    kindness:int
    other: int
    negative: int
    explanation: str


def send_prompt(prompt):
    client = OpenAI()
    api_key = os.getenv("OPENAI_API_KEY")
    chat_completion = client.beta.chat.completions.parse(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
        response_format=Compatibility
    )
    return chat_completion.choices[0].message.parsed

def get_overall_conversation_score(score):
    return (score.affection + score.vulnerability + score.kindness + score.other - score.negative) / 4

def ask_match(conversation):
    prompt = open("conversation_prompt.txt", "r").read()
    return send_prompt(prompt + conversation)

def ask_advice(conversations):
    prompt = open("person_prompt.txt", "r").read()
    for i in conversations:
        prompt += "\n\nConversation:\n" + i
    return send_prompt(prompt)

# heartrate given in timestamps of heartrate

example_scores = [18, 30, 56, 22, 36, 64, 58]
std = np.std(example_scores)

def get_10_score(heartrate_score):
    stds = (heartrate_score - np.average(example_scores))/std
    #print(heartrate_score - np.average(example_scores))
    #print("stds", stds)
    stds = stds * 3
    stds = stds + 5
    stds = min(stds, 10)
    stds = max(stds, 1)
    return math.ceil(stds)

def get_beats_after(time, diff):
    t = 0
    ans = 0
    for i in diff:
        t += i
        if (time + 30 > t and time < t):
            ans += 1
    return ans

def get_rates(heartrates):
    diff = []
    for i in range(1, len(heartrates)):
        if heartrates[i]-heartrates[i-1] < 2 and heartrates[i]-heartrates[i-1] > 0.25:
            diff.append(heartrates[i]-heartrates[i-1])
    rates = []

    for i in range(0, 100000, 5):
        x = get_beats_after(i, diff)
        if x == 0:
            break
        rates.append(x/0.5)
    # num_beats = 0
    # last_time = 0
    # time = 0
    # for i in diff:
    #     time += i
    #     num_beats = num_beats + 1
    #     if (time > last_time + 15):
    #         rates.append((num_beats-1)*60/15)
    #         num_beats = 1
    #         last_time = last_time + 15

    return rates

def get_absolute_score(heartrates):
    rates = get_rates(heartrates)
    rates.sort()
    rates = rates[1:len(rates)-1]
    n = len(rates)
    #print(rates)
    if (len(rates) == 0):
        return -10000000 #not enough time
    score = rates[math.floor(n*.9)]-rates[math.floor(n*.1)]
    return score

def get_heartrate_score(heartrates):
    score = get_absolute_score(heartrates)
    return get_10_score(score)
