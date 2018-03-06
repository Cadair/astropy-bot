import json
import time
import requests
from humanize import naturaltime, naturaldelta
from changebot.github.github_api import IssueHandler, RepoHandler, HOST
from changebot.github.github_auth import github_request_headers


from flask import Blueprint, request, current_app

circleci = Blueprint('circleci', __name__)


@circleci.route('/circleci', methods=['POST'])
def circleci_handler():
    if not request.data:
        print("No payload received")

    payload = json.loads(request.data)['payload']

    # Validate we have the keys we need, otherwise ignore the push
    required_keys = {'vcs_revision',
                     'username',
                     'reponame',
                     'status',
                     'build_num'}

    # if not required_keys.issubset(payload.keys()):
    #     return 'Payload missing {}'.format(' '.join(required_keys - payload.keys()))

    # optional_keys = {}
    # invalid_keys = payload.keys() - (required_keys | optional_keys)
    # if invalid_keys:
    #     return f"Received unknown values {' '.join(invalid_keys)}."

    # if "target_url" not in payload:
    #     payload['target_url'] = None

    # if payload['status'] == 'success':
    artifacts = get_artifacts_from_build(payload)
    url = get_documentation_url_from_artifacts(artifacts)
    print(url)
    installation = 86691
    if url:
        set_commit_status(f"{payload['username']}/{payload['reponame']}", installation,
                          payload['vcs_revision'], "success",
                          "Click details to preview the documentation build", url)
    # set_commit_status(**payload)

    return "All good"


def get_artifacts_from_build(p):
    base_url = "https://circleci.com/api/v1.1"
    query_url = f"{base_url}/project/github/{p['username']}/{p['reponame']}/{p['build_num']}/artifacts"
    print(query_url)
    response = requests.get(query_url)
    print(response)
    assert response.ok, response.content
    return response.json()


def get_documentation_url_from_artifacts(artifacts):
    for artifact in artifacts:
        # Find the root sphinx index.html
        if "html/index.html" in artifact['path']:
            return artifact['url']


def set_status(repository, commit_hash, state, description, context, *, headers, target_url=None):
    """
    Set status message in a pull request on GitHub.

    Parameters
    ----------
    state : { 'pending' | 'success' | 'error' | 'failure' }
        The state to set for the pull request.

    description : str
        The message that appears in the status line.

    context : str
        A string used to identify the status line.

    target_url : str or `None`
        Link to bot comment that is relevant to this status, if given.

    """

    data = {}
    data['state'] = state
    data['description'] = description
    data['context'] = context

    if target_url is not None:
        data['target_url'] = target_url

    url = f'{HOST}/repos/{repository}/statuses/{commit_hash}'
    response = requests.post(url, json=data, headers=headers)
    assert response.ok, response.content


def set_commit_status(repository, installation, commit_hash, state, description, target_url):

    headers = github_request_headers(installation)

    set_status(repository, commit_hash, state, description, "doc-preview-url",
               headers=headers, target_url=target_url)
