from datetime import datetime
import os
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import validators
import sys

proxy=None

def handle_exception(msg):
    with open("error_message.txt",'w') as f:
        f.write(msg)
    with open(os.environ["GITHUB_ENV"], "a") as f:
        f.write(f"ERROR_OCCURED=true\n")
    sys.exit(0)




def extract_channel_and_post_ids(text, min_count=1):
    pattern = r"(?:https?://)?t\.me/([^/\s]+)/(\d+)"
    matches = re.findall(pattern, text)
    if len(matches) < min_count:
        handle_exception(
            f"Could not find at least {min_count} valid Telegram URLs in the input."
        )
    return matches


def get_telegram_post_content(url):
    response = requests.get(url + "?embed=1&mode=tme", proxies=proxy)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    post_content = soup.find("div", class_="tgme_widget_message_text")
    time_el = soup.find("time", class_="datetime")
    forward_el = soup.find("a", class_="tgme_widget_message_forwarded_from_name")
    owner_el = soup.find("a", class_="tgme_widget_message_owner_name")

    if time_el:
        time_str = time_el.attrs["datetime"]
        time_val = datetime.fromisoformat(time_str)
    else:
        handle_exception("No time detected")
    if not owner_el:
        handle_exception("No owner detected")
    if forward_el:
        handle_exception(f"This post {url} is forwarded from {forward_el.attrs['href']}")

    return {
        "post_content": post_content.text if post_content else "",
        "owner_link": owner_el.attrs["href"],
        "time_val": time_val,
        "post_url": url,
    }


def extract_urls_from_issue_body(body):
    matches = extract_channel_and_post_ids(body, 2)
    tgc1, tgc2 = matches[0][0], matches[1][0]
    if tgc1 == tgc2:
        handle_exception(
            f"Telegram channels are the same. \ntgc1: {tgc1}\ntgc2: {tgc2}"
        )

    urls = [f"https://t.me/{channel}/{post_id}" for channel, post_id in matches[:2]]
    return urls[0], urls[1]


def validate_authenticity(orig_post: dict, violator_post: dict):
    threshold = float(os.environ.get("SIMILARITY_THRESHOLD", "0.8"))
    orig_ch_name, orig_post_id = extract_channel_and_post_ids(orig_post["owner_link"])[
        0
    ]
    vio_ch_name, vio_post_id = extract_channel_and_post_ids(
        violator_post["owner_link"]
    )[0]

    if orig_ch_name == vio_ch_name:
        handle_exception(f"Both posts are from the same origin")
    if not orig_post["time_val"] > violator_post["time_val"]:
        handle_exception(f"Original post's time is not prior to violator's post")

    similarity = check_similarity(
        orig_post["post_content"], violator_post["post_content"]
    )
    write_values(
        similarity,
        threshold,
        violator_post["post_url"],
        orig_post["post_url"],
        violator_content=violator_post["post_content"],
    )
    print(f"Similarity: {similarity}, Threshold: {threshold}")
    print(f"Violator URL: {violator_post['post_url']}")


def write_values(
    similarity, threshold, violator_post_url, orig_post_url, violator_content
):
    with open("violation_result.txt", "w") as f:
        f.write(f"VIOLATION_DETECTED={'true' if similarity > threshold else 'false'}\n")
        f.write(f"SIMILARITY={similarity}\n")
        f.write(f"VIOLATOR_URL={violator_post_url}\n")
        f.write(f"ORIG_URL={orig_post_url}\n")

    if similarity > threshold:
        with open("violation_detected", "w") as f:
            json.dump(
                {
                    "orig_post_url": orig_post_url,
                    "violator_post_url": violator_post_url,
                    "similarity": similarity,
                    "violator_content": violator_content,
                },
                f,
            )
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"VIOLATION_DETECTED=true\n")
            f.write(f"SIMILARITY={similarity}\n")
            f.write(f"VIOLATOR_URL={violator_post_url}\n")
            f.write(f"ORIG_URL={orig_post_url}\n")
        print("Violation detected and recorded.")
    else:
        print("No violation detected.")


def check_similarity(text1, text2):
    vectorizer = TfidfVectorizer().fit_transform([text1, text2])
    vectors = vectorizer.toarray()
    return cosine_similarity(vectors)[0][1]


def main():
    try:
        issue_number = os.environ["ISSUE_NUMBER"]
        token = os.environ["GITHUB_TOKEN"]
        repo_owner = os.environ["GITHUB_REPOSITORY"].split("/")[0]
        repo_name = os.environ["GITHUB_REPOSITORY"].split("/")[1]

        print(f"Processing issue number: {issue_number}")

        headers = {"Authorization": f"token {token}"}
        issue_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
        response = requests.get(issue_url, headers=headers, proxies=proxy)
        response.raise_for_status()
        issue_data = response.json()

        original_url, violator_url = extract_urls_from_issue_body(issue_data["body"])

        if not validators.url(original_url):
            handle_exception(f"Original URL not valid: {original_url}")
        if not validators.url(violator_url):
            handle_exception(f"Violator URL not valid: {violator_url}")

        original_content = get_telegram_post_content(original_url)
        violator_content = get_telegram_post_content(violator_url)

        validate_authenticity(original_content, violator_content)

    except Exception as e:
        error_message = str(e)
        print(f"Error occurred: {error_message}")
        # Write the error message to a file that can be read by GitHub Actions
        with open("error_message.txt", "w") as f:
            f.write(error_message)
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"ERROR_MESSAGE={error_message}\n")
        exit(1)


if __name__ == "__main__":
    main()
