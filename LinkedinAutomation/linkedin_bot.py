import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import os
import json

# 1. SETUP GOOGLE SHEETS
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# In GitHub Actions, we'll store the credentials in an environment variable
creds_dict = json.loads(os.environ['GOOGLE_CREDS'])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Your_Sheet_Name").sheet1 

# 2. FIND PENDING POST
records = sheet.get_all_records()
row_index = 2 # Starting after header
target_row = None

for row in records:
    if row['Status'] == 'Pending':
        target_row = row
        break
    row_index += 1

if not target_row:
    print("No pending articles found.")
    exit()

article_url = target_row['Article Link']

# 3. AI GENERATION (Using a Free API like Groq)
# You'll need a free API key from console.groq.com
def generate_post(url):
    prompt = f"Write a LinkedIn post based on this URL: {url}. Use the SarthAI structure: Hook, Pivot, Problem, Solution, and CTA. Make it professional."
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    return response.json()['choices'][0]['message']['content']

post_content = generate_post(article_url)

# 4. POST TO LINKEDIN
linkedin_url = "https://api.linkedin.com/v2/ugcPosts"
headers = {
    "Authorization": f"Bearer {os.environ['LINKEDIN_TOKEN']}",
    "X-Restli-Protocol-Version": "2.0.0"
}
post_data = {
    "author": f"urn:li:person:{os.environ['LINKEDIN_PERSON_ID']}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": post_content},
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
}

res = requests.post(linkedin_url, headers=headers, json=post_data)

# 5. UPDATE SHEET STATUS
if res.status_code == 201:
    sheet.update_cell(row_index, 2, "Posted")
    print("Successfully posted to LinkedIn!")
