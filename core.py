import os
import json
import time
import random
import datetime
import requests
from datetime import datetime, timedelta, UTC
from dateutil import parser
from dotenv import load_dotenv


WANTED_LANGUAGE = 'Python'
MAX_REPO_COUNT = 5000
MIN_STARS = 150
MAX_STARS = 300
MIN_PR_SEVEN_DAYS = 0 # this doesn't do anything right now
MIN_COMMIT_SEVEN_DAYS = 0 # doesn't do anything either
SEARCH_QUERIES = [
    f"language:python stars:{MIN_STARS}..{MAX_STARS} sort:updated"
] # if you wanna add more queries, go ahead


class GitHubScraper:
    def __init__(self, token=None, output_file="github_metrics.json"):
        self.token = token
        self.output_file = output_file
        self.headers = {
            'User-Agent': 'GitHub-Metrics-Collector',
        }
        if token:
            self.headers['Authorization'] = f'token {token}'
        self.results = {}
        self._load_existing_data()
        self.seven_days_ago = (datetime.now(UTC).replace(tzinfo=UTC) - timedelta(days=7)).isoformat()
    
    def _load_existing_data(self):
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    self.results = json.load(f)
                print(f"Loaded {len(self.results)} existing repository records")
            except json.JSONDecodeError:
                print("Error loading existing data. Starting with empty dataset.")
                self.results = {}
    
    def _save_results(self):
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=4)
    
    def _make_request(self, url, params=None):
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) == 0:
                reset_time = int(response.headers['X-RateLimit-Reset'])
                sleep_time = reset_time - time.time() + 5
                print(f"Rate limit exceeded. Sleeping for {sleep_time:.0f} seconds.")
                time.sleep(max(1, sleep_time))
                return self._make_request(url, params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            time.sleep(5)
            return None
    
    def search_repositories(self, query=SEARCH_QUERIES[0], page=1, per_page=30):
        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'updated',
            'order': 'desc',
            'page': page,
            'per_page': per_page
        }
        response = self._make_request(url, params)
        if not response:
            return []
        return response.get('items', [])
    
    def get_pull_requests(self, repo_full_name):
        url = f"https://api.github.com/repos/{repo_full_name}/pulls"
        params = {
            'state': 'all',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100
        }
        all_prs = []
        response = self._make_request(url, params)
        if not response:
            return []
        seven_days_ago_dt = parser.parse(self.seven_days_ago)
        for pr in response:
            updated_at = parser.parse(pr['updated_at'])
            if updated_at >= seven_days_ago_dt:
                all_prs.append(pr)
            else:
                break       
        return all_prs
    
    def get_issues(self, repo_full_name):
        url = f"https://api.github.com/repos/{repo_full_name}/issues"
        params = {
            'state': 'all',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100,
            'since': self.seven_days_ago
        }
        response = self._make_request(url, params)
        if not response:
            return []
        return [issue for issue in response if 'pull_request' not in issue]
    
    def get_commits(self, repo_full_name):
        url = f"https://api.github.com/repos/{repo_full_name}/commits"
        params = {
            'since': self.seven_days_ago,
            'per_page': 100
        }
        response = self._make_request(url, params)
        return response if response else []
    
    def calculate_avg_response_time(self, items, item_type):
        if not items:
            return None
        total_response_time = 0
        count = 0
        for item in items:
            created_at = parser.parse(item['created_at'])
            comments_url = item['comments_url']
            comments = self._make_request(comments_url)
            if comments and len(comments) > 0:
                creator_id = item['user']['id']
                for comment in comments:
                    if comment['user']['id'] != creator_id:
                        first_response = parser.parse(comment['created_at'])
                        response_time = (first_response - created_at).total_seconds() / 3600 
                        total_response_time += response_time
                        count += 1
                        break
        return round(total_response_time / count, 2) if count > 0 else None
    
    def process_repository(self, repo):
        repo_full_name = repo['full_name']
        print(f"processing repository: {repo_full_name}")
        if repo_full_name in self.results:
            print(f"already processed {repo_full_name}, skipping...")
            return
        try:
            pull_requests = self.get_pull_requests(repo_full_name)
            issues = self.get_issues(repo_full_name)
            commits = self.get_commits(repo_full_name)
            pr_response_time = self.calculate_avg_response_time(pull_requests, 'pr')
            issue_response_time = self.calculate_avg_response_time(issues, 'issue')
            self.results[repo_full_name] = {
                'repo_name': repo_full_name,
                'language': repo['language'],
                'stars': repo['stargazers_count'],
                'forks': repo['forks_count'],
                'pull_requests_last_7d': len(pull_requests),
                'issues_last_7d': len(issues),
                'commits_last_7d': len(commits),
                'avg_pr_response_time_hours': pr_response_time,
                'avg_issue_response_time_hours': issue_response_time,
                'collected_at': datetime.now(UTC).isoformat()
            }
            self._save_results()
        except Exception as e:
            print(f"error processing repository {repo_full_name}: {str(e)}")
        time.sleep(random.uniform(1, 3))
    
    def run(self, max_repos=100, search_queries=None):
        if search_queries is None:
            search_queries = SEARCH_QUERIES
        repositories_processed = 0
        for query in search_queries:
            page = 1
            while repositories_processed < max_repos:
                print(f"searching with query: {query}, page: {page}")
                repos = self.search_repositories(query, page)
                if not repos:
                    print(f"no more repositories found for query: {query}")
                    break
                for repo in repos:
                    if repositories_processed >= max_repos:
                        break
                    if (repo.get('language') == 'Python' and 
                        MIN_STARS <= repo.get('stargazers_count', 0) <= MAX_STARS):
                        self.process_repository(repo)
                        repositories_processed += 1
                        print(f"processed {repositories_processed}/{max_repos} repositories")
                    else:
                        print(f"skipping {repo['full_name']}")
                page += 1
                time.sleep(random.uniform(2, 5)) 
        print(f"completed processing {repositories_processed} repositories")
        self._save_results()

if __name__ == "__main__":
    load_dotenv()
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        raise Exception("Please use a github token, for that just enter the command GITHUB_TOKEN=your_token_here")
    scraper = GitHubScraper(token=github_token)
    scraper.run(max_repos=MAX_REPO_COUNT)