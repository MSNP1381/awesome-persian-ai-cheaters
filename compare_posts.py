
import os
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
proxy=None
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
    token = os.environ['GITHUB_TOKEN']
    
    # Get issue details
    headers = {'Authorization': f'token {token}'}
    issue_url = f'https://api.github.com/repos/OWNER/REPO/issues/{issue_number}'
    response = requests.get(issue_url, headers=headers,proxies=proxy)
    issue_data = response.json()
    
    # Extract URLs from issue body
    body_lines = issue_data['body'].split('\n')
    original_url = next((line for line in body_lines if 'Original Post Link:' in line), '').split(':')[-1].strip()
    violator_url = next((line for line in body_lines if 'Violator Post Link:' in line), '').split(':')[-1].strip()
    
    # Get content and check similarity
    original_content = get_telegram_post_content(original_url)
    violator_content = get_telegram_post_content(violator_url)
    similarity = check_similarity(original_content, violator_content)
    
    # If similarity is above threshold, create a file to signal violation
    if similarity > 0.8:
        with open('violation_detected', 'w') as f:
            json.dump({'violator_url': violator_url, 'similarity': similarity}, f)
