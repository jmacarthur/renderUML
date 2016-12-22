# Copyright (C) 2016 Codethink Limited

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import bottle
import os
import urllib
from os.path import expanduser
from bottle import route
import re
import subprocess
import logging
import sys

home = "/home/jimmacarthur"
plantumljar = os.path.join(home, "plantuml.jar")
repo_cache_dir = os.path.join(home, "renderUMLrepos")

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

def serve_error_image(error_name):
    image_file_name = os.path.join(["error-images", error_name + ".png"])
    if not os.path.exists(image_file_name):
        image_file_name = os.path.join(["error-images", "unknown-error.png"])
    try:
        with open(image_file_name, "rb") as f:
            image_data = f.read()
            return image_data
    except IOError as e:
        logging.error("Error serving the error image for '%s': %r"%(error_name, e))
    return None

@route('/renderUML/<name:path>')
def render(name):
    ref = None
    if "HTTP_REFERER" in bottle.request.environ: ref = bottle.request.environ['HTTP_REFERER']
    if not os.path.isdir(repo_cache_dir):
        os.mkdir(repo_cache_dir)

    # No idea why, but with WSGI on, some double slashes get converted to single ones in the URL.
    if re.search("https:\/[^\/]", name):
        name = name.replace("https:/", "https://")

    if not re.search("https:\/\/", name):
        # The repository must have a https prefix; we cannot clone over SSH.

    # URLs should be in the form <repository URL>:<page path>, but the URL will have a colon in it,
    # so we'll split into three and recombine rather than try and split just on the second colon.
    fields = name.split(":")
    protocol = fields[0]
    git_server_and_path = fields[1].strip("/")
    page = fields[2].strip("/")

    path_components = git_remote.split("/")
    server = path_components[0]
    repository_name = "/".join(path_components[1:])

    if server not in git_server_whitelist:
        logging.error("Server %s rejected"%server)
        return serve_error_image("bad-domain")
    if not any(repository_name.startswith(x) for x in repo_prefix_whitelist):
        logging.error("Repository_name %s rejected"%repository_name)
        return serve_error_image("bad-repo")

    logging.info("Server is %s"%server)
    git_remote = "%s:%s"%(protocol, git_server_and_path)

    (pagename, oldext) = os.path.splitext(page)
    pagename += ".md"
    logging.info("git_remote is %s"%git_remote)
    logging.info("pagename is %s"%pagename)
    gitdir = os.path.join(repo_cache_dir, os.path.basename(git_remote))

    logging.info("gitdir is %s"%gitdir)

    if not os.path.isdir(gitdir):
        logging.error("%s is not a directory" % gitdir)
        # OK, try and clone it
        res = subprocess.call(["git","clone", git_remote, gitdir])
        if res != 0:
            logging.error("Failed to clone git directory")
            return serve_error_image("clone-failed")

    if not sanity_check(gitdir):
        logging.error("Aborting due to unorthodox characters in %s"%gitdir)
        return serve_error_image("bad-input")

    if not sanity_check(pagename):
        logging.error("Aborting due to unorthodox characters in %s"%pagename)
        return serve_error_image("bad-input")

    # Attempt to update the repository
    update_repo(gitdir)

    with open(os.path.join(gitdir, pagename), "rt") as f:
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
                logging.info("Potential link line found")
                if uml_lines != []:
                    logging.info("rendering UML extracted from page")
                    return renderUML("\n".join(uml_lines))
                else:
                    logging.warning("No UML found")
                break
            else:
                if record: uml_lines.append(l)


    return serve_error_image("no-uml")
