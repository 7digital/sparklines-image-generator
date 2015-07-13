"""spark_flask.py

A web service for generating sparklines with the Flask framework.

More or less a transliteration of the original spark.cgi by Joe Gregorio (https://github.com/jcgregorio/sparklines).

Requires the Python Imaging Library and Flask
"""

__author__ = "Matthew Gray"
__contributors__ = ['Alan Powell', 'Joe Gregorio']
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

from flask import Flask, Response, request, make_response
import hashlib
from pngcanvas import PNGCanvas
import rgb
import StringIO

app = Flask(__name__)

def plot_sparkline_discrete(results, args, longlines=False):
    """The source data is a list of values between
      0 and 100 (or 'limits' if given). Values greater than 95 
      (or 'upper' if given) are displayed in red, otherwise 
      they are displayed in green"""
    width = int(args.get('width', '2'))
    height = int(args.get('height', '14'))
    upper = int(args.get('upper', '50'))
    below_color = args.get('below-color', 'gray')
    above_color = args.get('above-color', 'red')
    gap = 4
    if longlines:
        gap = 0
    im = PNGCanvas(len(results)*width-1, height)
    im.color = rgb.colors['white']
    im.filledRectangle(0, 0, im.width-1, im.height-1)

    (dmin, dmax) = [int(x) for x in args.get('limits', '0,100').split(',')]
    if dmax < dmin:
        dmax = dmin
    zero = im.height - 1
    if dmin < 0 and dmax > 0:
        zero = im.height - (0 - dmin) / (float(dmax - dmin + 1) / (height - gap))
    for (r, i) in zip(results, range(0, len(results)*width, width)):
        color = (r >= upper) and above_color or below_color
        if r < 0:
            y_coord = im.height - (r - dmin) / (float(dmax - dmin + 1) / (height - gap))
        else:
            y_coord = im.height - (r - dmin) / (float(dmax - dmin + 1) / (height - gap))
        im.color = rgb.colors[color]
        if longlines:
            im.filledRectangle(i, zero, i+width-2, y_coord)
        else:
            im.rectangle(i, y_coord - gap, i+width-2, y_coord)
    return im.dump()

def plot_sparkline_smooth(results, args):
   step = int(args.get('step', '2'))
   height = int(args.get('height', '20'))
   (dmin, dmax) = [int(x) for x in args.get('limits', '0,100').split(',')]
   im = PNGCanvas((len(results)-1)*step+4, height)
   im.color = rgb.colors['white']
   im.filledRectangle(0, 0, im.width-1, im.height-1)

   coords = zip(range(1,len(results)*step+1, step), [height - 3  - (y-dmin)/(float(dmax - dmin +1)/(height-4)) for y in results])
   im.color = [128, 128, 128, 255]
   lastx, lasty = coords[0]
   for x0, y0, in coords:
     im.line(lastx, lasty, x0, y0)
     lastx, lasty = x0, y0
   min_color = rgb.colors[args.get('min-color', 'green')]
   max_color = rgb.colors[args.get('max-color', 'red')]
   last_color = rgb.colors[args.get('last-color', 'blue')]
   has_min = args.get('min-m', 'false')
   has_max = args.get('max-m', 'false')
   has_last = args.get('last-m', 'false')
   if has_min == 'true':
      min_pt = coords[results.index(min(results))]
      im.color = min_color
      im.rectangle(min_pt[0]-1, min_pt[1]-1, min_pt[0]+1, min_pt[1]+1)
   if has_max == 'true':
      im.color = max_color
      max_pt = coords[results.index(max(results))]
      im.rectangle(max_pt[0]-1, max_pt[1]-1, max_pt[0]+1, max_pt[1]+1)
   if has_last == 'true':
      im.color = last_color
      end = coords[-1]
      im.rectangle(end[0]-1, end[1]-1, end[0]+1, end[1]+1)
   return im.dump()

def plot_error(results, args):
   im = PNGCanvas(40, 15)
   im.color = rgb.colors['red']
   im.line(0, 0, im.width, im.height)
   im.line(0, im.height, im.width, 0)
   return im.dump()

plot_types = {
  'discrete': plot_sparkline_discrete,
  'impulse': lambda data, args: plot_sparkline_discrete(data, args, True),
  'smooth': plot_sparkline_smooth,
  'error': plot_error
}

@app.route("/spark.cgi")
@app.route("/sparkline")
def sparkline():

  etag = str(hashlib.sha1(request.query_string).hexdigest())
  if etag == request.headers.get("If-None-Match", ""):
    return ("304: Not modified", 304)

  raw_data = request.args.get('d', '')

  if not raw_data:
    return ("Status: 400 No data supplied", 400)
  
  (data_min, data_max) = [int(x) for x in request.args.get('limits', '0,100').split(',')]
  data = [int(d) for d in raw_data.split(",") if d]
  if min(data) < data_min or max(data) > data_max:
    return ("Status: 400 Data out of range", 400)

  args = request.args
  type = args.get('type', 'discrete')
  if not plot_types.has_key(type):
      error("Status: 400 Unknown plot type.")

  image_data = plot_types[type](data, args)

  response = make_response(image_data, 200)
  response.headers["Content-Type"] = "image/png"
  response.headers["Etag"] = str(hashlib.sha1(request.query_string).hexdigest())
  
  return response


if __name__ == "__main__":
  app.run()
