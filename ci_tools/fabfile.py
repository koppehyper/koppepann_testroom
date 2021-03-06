#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import run
from fabric.api import local
from fabric.api import task
from fabric.api import abort
import os
import requests


def get_my_ip():
    my_ip = local('dig +short myip.opendns.com @resolver1.opendns.com',
                  capture=True)
    return my_ip


def open_sg():
    sg_id = os.environ.get('MY_SECURITY_GROUP')
    my_ip = get_my_ip()
    local('aws ec2 authorize-security-group-ingress --group-id ' +
          '%s --protocol tcp --port 22 --cidr %s/32' % (sg_id, my_ip))


def close_sg():
    sg_id = os.environ.get('MY_SECURITY_GROUP')
    my_ip = get_my_ip()
    local('aws ec2 revoke-security-group-ingress --group-id ' +
          '%s --protocol tcp --port 22 --cidr %s/32' % (sg_id, my_ip))


@task
def test():
    try:
        open_sg()
        check_remote_branch()
        run('echo `date` >> /root/deploy.log')
        git_merge()
        slack()
    except:
        delete_branch()
        slack(msg='Error! Please handle this problem!')
        abort('error!')
    finally:
        close_sg()


def check_remote_branch():
    branch_list = local('git branch -a', capture=True)
    print branch_list
    branch = 'remotes/origin/%s' % os.environ.get('CIRCLE_BRANCH')
    if branch not in branch_list:
        raise ('Not Exist Branch : %s' % branch)


@task
def delete_branch():
    circle_branch = os.environ.get('CIRCLE_BRANCH')
    local("git push origin :%s" % circle_branch)


def git_merge():
    circle_branch = os.environ.get('CIRCLE_BRANCH')
    local("git config --global user.name 'Koppe Pan'")
    local("git config --global user.email 'koppehyper@gmail.com'")
    local("./hub pull-request -m 'Test PullRequest'")
    local("git checkout master")
    local("git pull")
    local("git merge --no-ff %s -m 'Merge master'" % circle_branch)
    local("git push origin master")
    delete_branch()


def slack(msg=None):
    api_baseuri = "https://slack.com/api"
    method = "chat.postMessage"
    uri = "%s/%s" % (api_baseuri, method)
    token = os.environ.get('SLACK_TOKEN')

    project_name = os.environ.get('CIRCLE_PROJECT_USERNAME')
    repo_name = os.environ.get('CIRCLE_PROJECT_REPONAME')
    build_no = os.environ.get('CIRCLE_BUILD_NUM')

    if msg is None:
        msg = 'MERGED > https://circleci.com/gh/%s/%s/%s' % (
            project_name, repo_name, build_no)

    channel = '#testroom'
    username = 'Hogehoge'
    icon_url = ':dora:'

    param = {"token": token,
             "channel": channel,
             "text": msg,
             "username": username,
             "link_names": True,
             "icon_emoji": icon_url}

    requests.get(uri, params=param, verify=False)
