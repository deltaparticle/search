# webfinder/finder.py

import requests, os, time, json
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from PyPDF2 import PdfReader
from urllib.parse import urlparse

headers = {
    "User-Agent": "Mozilla/5.0"
}

def search_person(name, api_key, output_dir="scraped_data"):
    os.makedirs(output_dir, exist_ok=True)

    queries = [
        f'site:linkedin.com/in "{name}"',
        f'site:github.com "{name}"',
        f'site:instagram.com "{name}"',
        f'filetype:pdf "{name}" resume',
        f'filetype:doc "{name}" resume',
        f'filetype:txt "{name}" resume',
        f'"{name}" contact info',
        f'"{name}" email resume',
        f'"{name}" CV filetype:pdf'
    ]

    def search_google_serpapi(query):
        search = GoogleSearch({
            "q": query,
            "api_key": api_key,
            "num": 3
        })
        result = search.get_dict()
        return result.get("organic_results", [])

    def download_file(url, filename):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            with open(filename, "wb") as f:
                f.write(res.content)
            return True
        except:
            return False

    def extract_pdf_text(url):
        temp_file = "temp.pdf"
        if download_file(url, temp_file):
            try:
                reader = PdfReader(temp_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                os.remove(temp_file)
                return text[:2000]
            except:
                return "[PDF Read Error]"
        return "[PDF Download Failed]"

    def parse_github_repo(url):
        try:
            html = requests.get(url, headers=headers).text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.find("strong", {"itemprop": "name"})
            description = soup.find("p", {"class": "f4 my-3"})
            readme = soup.find("article", {"class": "markdown-body"})
            return {
                "repo_name": title.text.strip() if title else None,
                "description": description.text.strip() if description else None,
                "readme_snippet": readme.get_text().strip()[:1500] if readme else "No README found"
            }
        except Exception as e:
            return {"error": str(e)}

    def scrape_html(url):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            return soup.get_text()[:2000]
        except Exception as e:
            return f"[HTML Scrape Error]: {e}"

    def is_result_relevant(content):
        if isinstance(content, str):
            return name.lower() in content.lower() and len(content) > 300
        elif isinstance(content, dict):
            combined = json.dumps(content).lower()
            return name.lower() in combined and len(combined) > 300
        return False

    # --- MAIN LOOP ---
    results = {}
    for query in queries:
        search_results = search_google_serpapi(query)
        results[query] = {}

        for res in search_results[:3]:
            url = res.get("link")
            snippet = res.get("snippet") or res.get("title", "")
            if not url:
                continue

            if "linkedin.com/in" in url:
                results[query][url] = {"summary_snippet": snippet}
                continue

            parsed = urlparse(url)
            domain = parsed.netloc
            content = ""

            try:
                if url.endswith(".pdf"):
                    content = extract_pdf_text(url)
                elif "github.com" in domain:
                    content = parse_github_repo(url)
                elif url.endswith(".txt") or url.endswith(".doc"):
                    content = scrape_html(url)
                else:
                    content = scrape_html(url)
            except Exception as e:
                content = f"[Error]: {e}"

            if is_result_relevant(content):
                results[query][url] = content
            else:
                results[query][url] = "[Possibly Irrelevant]"

            time.sleep(1)

    # Save
    output_file = os.path.join(output_dir, f"{name.replace(' ', '_')}_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return output_file
