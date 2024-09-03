import json
import re
import sys


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


def get_description(json_data: dict):
    (orig_post_url, violator_post_url, similarity, violator_content) = (
        json_data.values()
    )
    violator_channel, _ = extract_channel_and_post_ids(violator_post_url)[0]
    violator_tg_link = f"https://t.me/{violator_channel}"
    with open("violatoin_template.md") as f:
        text = f.read()
    text.format(
        {
            "violator_tg_link": violator_tg_link,
            "orig_link": orig_post_url,
            "violator_post_url": violator_post_url,
            "violaotr_content": violator_content,
            'similarity_value':similarity
        }
    )
    return text


def update_readme(data):
    try:
        with open("README.md", "r+") as f:
            text=get_description(data)
            f.write(text)
        print(f"Successfully added new violator: {data["violator_url"]}")
    except IOError as e:
        print(f"Error updating README.md: {str(e)}", file=sys.stderr)
        raise


def main():
    try:
        with open("violation_detected", "r") as f:
            data = json.load(f)

        update_readme(data["violator_url"], data["similarity"])
        return 0
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
