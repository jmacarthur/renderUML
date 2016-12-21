# Copyright (C) 2016 Codethink Limited
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import bottle
import os
import urllib
from os.path import expanduser
from bottle import route
import re
import subprocess
import pygit2
import logging
import sys

plantumljar = expanduser("~/trustable/plantuml.jar")
repo_cache_dir = expanduser("~/renderUMLrepos")

git_server_whitelist = [ "gitlab.com" ]
repo_prefix_whitelist = [ "trustable" ]

@route('/hello')
def hello():
    return "Hello World!"

@route('/')
def main():
    return bottle.redirect("/about")

@route('/about')
def about():
    return "Placeholder text for information about renderUML"

def renderUML(umltext):

    cmd = ["java", "-jar", plantumljar, "-tpng", "-p"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)
    (png, err) = p.communicate(umltext)
    bottle.response.content_type = 'image/png'
    return png

def update_repo(gitdir):
    subprocess.call(["git", "-C", gitdir, "pull"])
    # TODO: Check return value

def sanity_check(path):
    return re.match('^[a-zA-Z/:.-]*$', path) != None
    
@route('/renderUML/<name:path>')
def render(name):
    ref = None
    if "HTTP_REFERER" in bottle.request.environ: ref = bottle.request.environ['HTTP_REFERER']
    if not os.path.isdir(repo_cache_dir):
        os.mkdir(repo_cache_dir)

    ## TODO: Figure out repo from referrer...
    fields = name.split(":")
    protocol = fields[0]
    git_remote = fields[1]
    page = fields[2]

    path_components = git_remote.split("/")
    server = path_components[2]
    repository_name = "/".join(path_components[3:])
    
    if server not in git_server_whitelist:
        print "Server %s rejected"%server
        return None
    if not any(repository_name.startswith(x) for x in repo_prefix_whitelist):
        print "repository_name %s rejected"%repository_name
        return None
    print "Server is %s"%server
    git_remote = "%s:%s"%(protocol, git_remote)

    if page[0] == "/": page = page[1:]
    (pagename, oldext) = os.path.splitext(page)
    pagename += ".md"
    print "git_remote is %s"%git_remote
    print "pagename is %s"%pagename
    gitdir = os.path.join(repo_cache_dir, os.path.basename(git_remote))
    print "gitdir is %s"%gitdir
    if not os.path.isdir(gitdir):
        logging.error("%s is not a directory" % gitdir)
        # OK, try and clone it
        res = subprocess.call(["git","clone", git_remote, gitdir])
        if res != 0:
            return "Failed to clone git directory"

    if not sanity_check(gitdir):
        print "Aborting due to unorthodox characters in %s"%gitdir
        return None

    if not sanity_check(pagename):
        print "Aborting due to unorthodox characters in %s"%pagename
        return None
        
    # Attempt to update it
    update_repo(gitdir)

    with open(os.path.join(gitdir, pagename), "rt") as f:
        print "Reading file"
        uml_lines = []
        record = False
        while True:
            l = f.readline()
            if l == "": break
            l = l.strip()
            print l
            if re.match("\s*<!---\s*", l):
                uml_lines = []
                record = True
            elif re.match("\s*-->\s*", l):
                record = False
            elif re.search("\/renderUML\/%s"%name, l):
                print "Potential link line found"
                if uml_lines != []:
                    print "rendering UML extracted from page"
                    return renderUML("\n".join(uml_lines))
                else:
                    print "No UML found"
                break
            else:
                if record: uml_lines.append(l)


    # I can't return an error image yet. This will probably not be visible, but
    # it's better than nothing.
    return "Rendering failed"
