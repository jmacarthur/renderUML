#!/usr/bin/env python
import bottle
import renderUML

bottle.run(host='0.0.0.0',
           port=8080,
           server="wsgiref")

