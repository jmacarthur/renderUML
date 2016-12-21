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

plantumljar = expanduser("~/Downloads/plantuml.jar")

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


@route('/renderUML/<name>')
def render(name):
    ref = None
    if "HTTP_REFERER" in bottle.request.environ: ref = bottle.request.environ['HTTP_REFERER']

    ## TODO: Figure out repo from referrer...
    repo = expanduser("~/temp/overview.wiki")
    page = "pages/plantuml-example.md"
    with open(os.path.join(repo, page), "rt") as f:
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
