proxy=None

import os
import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import validators

def extract_urls_from_issue_body(body):
    # Regex pattern for Telegram URLs
    pattern = r'(?:https?://)?t\.me/([^/\s]+)/(\d+)'
    matches = re.findall(pattern, body)
    
    if len(matches) < 2:
        return None, None
    tgc1,tgc2=matches[0][0],matches[1][0]
    if tgc1==tgc2:
        raise Exception(f"telegram channels are the same. \ntgc1 :{tgc1}\ntgc2:{tgc2}")
    # Construct full URLs
    urls = [f'https://t.me/{channel}/{post_id}' for channel, post_id in matches]
    
    return urls[0], urls[1] 
def get_telegram_post_content(url):
    response = requests.get(url+"?embed=1&mode=tme",proxies=proxy)
    soup = BeautifulSoup(response.text, 'html.parser')
    post_content = soup.find('div', class_='tgme_widget_message_text')
    return post_content.text if post_content else ''

def check_similarity(text1, text2):
    vectorizer = TfidfVectorizer().fit_transform([text1, text2])
    vectors = vectorizer.toarray()
    return cosine_similarity(vectors)[0][1]

def main():
    issue_number = os.environ['ISSUE_NUMBER']
    print(issue_number)
    token = os.environ['GITHUB_TOKEN']
    
    # Get issue details
    headers = {'Authorization': f'token {token}'}
    issue_url = f'https://api.github.com/repos/MSNP1381/awesome-persian-ai-cheaters/issues/{issue_number}'
    response = requests.get(issue_url, headers=headers,proxies=proxy)
    issue_data = response.json()

    
    original_url,violator_url=extract_urls_from_issue_body(issue_data['body'])

    if not validators.url(original_url): raise Exception(f"original url not valid \n url:{original_url}")
    if not validators.url(violator_url): raise Exception(f"violator url not valid \n url:{original_url}")
    # Get content and check similarity
    original_content = get_telegram_post_content(original_url)
    violator_content = get_telegram_post_content(violator_url)
    similarity = check_similarity(original_content, violator_content)
    # If similarity is above threshold, create a file to signal violation
    print({'violator_url': violator_url, 'similarity': similarity})
    if similarity > 0.8:
        with open('violation_detected', 'w') as f:
            json.dump({'violator_url': violator_url, 'similarity': similarity}, f)
        with open(os.environ['GITHUB_ENV'], 'a') as env_file:
            env_file.write("VIOLATION_DETECTED=true")
            env_file.write(f"SIMILARITY={similarity:.2f}")
            env_file.write(f"VIOLATOR_URL={violator_url}")
    else:
        with open(os.environ['GITHUB_ENV'], 'a') as env_file:
            env_file.write("VIOLATION_DETECTED=false")