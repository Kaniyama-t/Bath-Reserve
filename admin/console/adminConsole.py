from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

app = Blueprint('adminConsole', __name__, template_folder='templates')

@app.route('/', defaults={'page': 'index'})
@app.route('/<page>')
def show(page):
    try:
        return render_template('adminConsole/%s.html' % page)
    except TemplateNotFound:
        abort(404)
