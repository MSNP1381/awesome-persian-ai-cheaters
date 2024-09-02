import os
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import validators
import sys

proxy = None


def extract_urls_from_issue_body(body):
    pattern = r"(?:https?://)?t\.me/([^/\s]+)/(\d+)"
    matches = re.findall(pattern, body)

    if len(matches) < 2:
        raise ValueError("Could not find two valid Telegram URLs in the issue body.")

    tgc1, tgc2 = matches[0][0], matches[1][0]
    if tgc1 == tgc2:
        raise ValueError(
            f"Telegram channels are the same. \ntgc1: {tgc1}\ntgc2: {tgc2}"
        )

    urls = [f"https://t.me/{channel}/{post_id}" for channel, post_id in matches[:2]]
    return urls[0], urls[1]


def get_telegram_post_content(url):
    response = requests.get(url + "?embed=1&mode=tme", proxies=proxy)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    post_content = soup.find("div", class_="tgme_widget_message_text")
    return post_content.text if post_content else ""


def check_similarity(text1, text2):
    vectorizer = TfidfVectorizer().fit_transform([text1, text2])
    vectors = vectorizer.toarray()
    return cosine_similarity(vectors)[0][1]


def main():
    issue_number = os.environ["ISSUE_NUMBER"]
    token = os.environ["GITHUB_TOKEN"]
    repo_owner = os.environ["GITHUB_REPOSITORY"].split("/")[0]
    repo_name = os.environ["GITHUB_REPOSITORY"].split("/")[1]
    threshold = float(os.environ.get("SIMILARITY_THRESHOLD", "0.8"))

    print(f"Processing issue number: {issue_number}")

    headers = {"Authorization": f"token {token}"}
    issue_url = (
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
    )
    response = requests.get(issue_url, headers=headers, proxies=proxy)
    response.raise_for_status()
    issue_data = response.json()

    original_url, violator_url = extract_urls_from_issue_body(issue_data["body"])

    if not validators.url(original_url):
        raise ValueError(f"Original URL not valid: {original_url}")
    if not validators.url(violator_url):
        raise ValueError(f"Violator URL not valid: {violator_url}")

    original_content = get_telegram_post_content(original_url)
    violator_content = get_telegram_post_content(violator_url)
    similarity = check_similarity(original_content, violator_content)

    print(f"Similarity: {similarity}, Threshold: {threshold}")
    print(f"Violator URL: {violator_url}")

    with open("violation_result.txt", "w") as f:
        f.write(f"VIOLATION_DETECTED={'true' if similarity > threshold else 'false'}\n")
        f.write(f"SIMILARITY={similarity}\n")
        f.write(f"VIOLATOR_URL={violator_url}\n")

    if similarity > threshold:
        with open("violation_detected", "w") as f:
            json.dump({"violator_url": violator_url, "similarity": similarity}, f)
        print("Violation detected and recorded.")
    else:
        print("No violation detected.")

    return 0


if __name__ == "__main__":
    main()
