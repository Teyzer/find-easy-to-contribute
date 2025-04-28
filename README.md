# Find projects easy to contribute to

This projects, which scrapes a part of the recently updated github projects, allows to find projects which are very active, so that you find people ready to help you make your first steps.

You have a few settings you can edit at the top of the `core.py`, by default, it finds projects in Python, between 150 and 300 stars. If you launch the script as is, it will run until 5000 repositories are scrapped, and you can stop at any moment, everything is saved inside a generated `github_metrics.json`, which will contain of the following format:

```json
    "some_owner/some_repo": {
        "repo_name": "some_owner/some_repo",
        "language": "Python",
        "stars": 270,
        "forks": 63,
        "pull_requests_last_7d": 31,
        "issues_last_7d": 3,
        "commits_last_7d": 24,
        "avg_pr_response_time_hours": 8.89,
        "avg_issue_response_time_hours": 30.45,
        "collected_at": "2025-04-28T14:04:50.252180+00:00"
    },
```

## How to use 

Just `git clone` that repository, then (after creating a virtual environment if you want to), install the requirements:
```
pip install -r requirements.txt
```

Then create a file named `.env` in the root of the project, and add your github token inside, like this:
```
GITHUB_TOKEN=your_github_token
```
You can create a github token by going to github > settings > developer settings > personal access tokens > tokens (classic) > generate new token. Make sure to give it the `repo` scope, and copy the token.

Then you can run the script:
```
python3 core.py
```

Again, you can edit the head of the `core.py` file to change the settings, and you can stop the script at any time, it will save the progress in the `github_metrics.json` file.