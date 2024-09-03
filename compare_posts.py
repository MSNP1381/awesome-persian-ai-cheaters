from datetime import datetime
import os
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import validators


proxy = None


def extract_channel_and_post_ids(text, min_count=1):
    """
    Extracts channel names and post IDs from the given text containing Telegram URLs.

    Parameters:
        text (str): The input text containing one or more Telegram URLs.
        min_count (int): The minimum number of URL matches required. Defaults to 1.

    Returns:
        list: A list of tuples, each containing a channel name and a post ID.

    Raises:
        ValueError: If fewer matches than min_count are found.
    """
    # Define the regular expression pattern
    pattern = r"(?:https?://)?t\.me/([^/\s]+)/(\d+)"

    # Use re.findall to match the pattern in the given text
    matches = re.findall(pattern, text)

    # Check if there are enough matches
    if len(matches) < min_count:
        raise ValueError(
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
        raise Exception("no time detected")
    if not owner_el:
        raise Exception("no owner detected")
    if forward_el:
        raise Exception(f"this post {url} is forwarded from {forward_el.attrs['href']}")
    return {
        "post_content": post_content.text if post_content else "",
        "owner_link": owner_el.attrs["href"],
        "time_val": time_val,
        "post_url": url,
    }


def extract_urls_from_issue_body(body):

    matches = extract_channel_and_post_ids(body,2)

    tgc1, tgc2 = matches[0][0], matches[1][0]
    if tgc1 == tgc2:
        raise ValueError(
            f"Telegram channels are the same. \ntgc1: {tgc1}\ntgc2: {tgc2}"
        )

    urls = [f"https://t.me/{channel}/{post_id}" for channel, post_id in matches[:2]]
    return urls[0], urls[1]


def validate_authenticity(orig_post: dict, voilator_post: dict):
    threshold = float(os.environ.get("SIMILARITY_THRESHOLD", "0.8"))

    orig_ch_name, orig_post_id = extract_channel_and_post_ids(orig_post["owner_link"])
    vio_ch_name, vio_post_id = extract_channel_and_post_ids(voilator_post["owner_link"])
    if orig_ch_name == vio_ch_name:
        raise Exception(f"both posts are from same origin")
    if not orig_post["time_val"] > voilator_post["time_val"]:
        raise Exception(f"original's post time is not prior to violators post")

    similarity = check_similarity(
        orig_post["post_content"], voilator_post["post_content"]
    )
    write_values(
        similarity, threshold, voilator_post["post_url"], orig_post["post_url"],violator_content=voilator_post['post_content']
    )
    print(f"Similarity: {similarity}, Threshold: {threshold}")
    print(f"Violator URL: {voilator_post['post_url']}")


def write_values(similarity, threshold, violator_post_url, orig_post_url,violator_content):
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
                    'violator_content':violator_content
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
    issue_number = os.environ["ISSUE_NUMBER"]
    token = os.environ["GITHUB_TOKEN"]
    repo_owner = os.environ["GITHUB_REPOSITORY"].split("/")[0]
    repo_name = os.environ["GITHUB_REPOSITORY"].split("/")[1]

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
    # similarity = check_similarity(original_content, violator_content)
    validate_authenticity(original_content,
violator_content)


    return 0


if __name__ == "__main__":
    main()
