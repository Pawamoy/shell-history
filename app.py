# -*- coding: utf-8 -*-

import time
from collections import Counter, defaultdict
from datetime import datetime
import statistics

from flask import Flask, jsonify, render_template
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import extract, func, select

import db


# Initialization and constants ------------------------------------------------
app = Flask(__name__)
app.secret_key = '2kQOLbr6NtfHV0wIItjHWzuwsgCUXA4CSSBWFE9yELqrkSZU'
db.create_tables()
session = db.Session()


# Flask Admin stuff -----------------------------------------------------------
class HistoryModelView(ModelView):
    can_create = False
    can_delete = True
    can_view_details = True
    create_modal = True
    edit_modal = True
    can_export = True
    page_size = 50

    list_template = 'admin/history_list.html'

    column_exclude_list = ['parents']
    column_searchable_list = [
        'id', 'start', 'stop', 'duration', 'host', 'user', 'uuid', 'tty',
        'parents', 'shell', 'level', 'type', 'code', 'path', 'cmd'
    ]
    column_filters = [
        'host', 'user', 'uuid', 'tty', 'parents',
        'shell', 'level', 'type', 'code', 'path', 'cmd'
    ]
    column_editable_list = [
        'host', 'user', 'uuid', 'tty',
        'shell', 'level', 'type', 'code', 'path', 'cmd'
    ]
    form_excluded_columns = ['start', 'stop', 'duration']
    # form_widget_args = {
    #     'start': {'format': '%Y-%m-%d %H:%M:%S.%f'},
    #     'stop': {'format': '%Y-%m-%d %H:%M:%S.%f'},
    #     'duration': {'format': '%Y-%m-%d %H:%M:%S.%f'}
    # }


admin = Admin(app, name='Shell History Admin', template_mode='bootstrap3')
admin.add_view(HistoryModelView(db.History, session))


# Utils -----------------------------------------------------------------------
def since_epoch(date):
    return time.mktime(date.timetuple())


def fractional_year(start, end):
    this_year = end.year
    this_year_start = datetime(year=this_year, month=1, day=1)
    next_year_start = datetime(year=this_year + 1, month=1, day=1)
    time_elapsed = since_epoch(end) - since_epoch(start)
    year_duration = since_epoch(next_year_start) - since_epoch(this_year_start)
    return time_elapsed / year_duration


# Special views ---------------------------------------------------------------
@app.route('/')
def home_view():
    return render_template('home.html')


@app.route('/update')
def update_call():
    data = {'message': None, 'class': None}
    try:
        changed = db.update()
    except Exception as e:
        data['class'] = 'alert-danger'
        data['message'] = '%s\n%s: %s' % (
            'Failed to import current history. '
            'The following exception occured:',
            type(e), e
        )
    else:
        if changed:
            data['class'] = 'alert-info'
            data['message'] = (
                'Database successfully updated, '
                'refresh the page to see the change.'
            )
        else:
            data['class'] = 'alert-success'
            data['message'] = 'Database already synchronized, nothing changed.'

    return jsonify(data)


# Simple views rendering templates --------------------------------------------
@app.route('/daily')
def daily_view():
    return render_template('daily.html')


@app.route('/fuck')
def fuck_view():
    return render_template('fuck.html')


@app.route('/hourly')
def hourly_view():
    return render_template('hourly.html')


@app.route('/hourly_average')
def hourly_average_view():
    return render_template('hourly_average.html')


@app.route('/length')
def length_view():
    return render_template('length.html')


@app.route('/markov')
def markov_view():
    return render_template('markov.html')


@app.route('/markov_full')
def markov_full_view():
    return render_template('markov_full.html')


@app.route('/monthly')
def monthly_view():
    return render_template('monthly.html')


@app.route('/monthly_average')
def monthly_average_view():
    return render_template('monthly_average.html')


@app.route('/top_commands_full')
def top_commands_full_view():
    return render_template('top_commands_full.html')


@app.route('/top_commands')
def top_commands_view():
    return render_template('top_commands.html')


@app.route('/trending')
def trending_view():
    return render_template('trending.html')


@app.route('/type')
def type_view():
    return render_template('type.html')


# Routes to return JSON contents ----------------------------------------------
@app.route('/daily_json')
def daily_json():
    data = None
    return jsonify(data)


@app.route('/fuck_json')
def fuck_json():
    data = None
    return jsonify(data)


@app.route('/hourly_json')
def hourly_json():
    results = defaultdict(lambda: 0)
    results.update(session.query(
            extract('hour', db.History.start).label('hour'),
            func.count('hour')
        ).group_by('hour').all())
    data = [results[hour] for hour in range(0, 24)]
    return jsonify(data)


@app.route('/hourly_average_json')
def hourly_average_json():
    mintime = session.query(func.min(db.History.start)).first()[0]
    maxtime = session.query(func.max(db.History.start)).first()[0]
    number_of_days = (maxtime - mintime).days + 1
    results = defaultdict(lambda: 0)
    results.update(session.query(
            extract('hour', db.History.start).label('hour'),
            func.count('hour')
        ).group_by('hour').all())
    data = [float('%.2f' % (results[hour] / number_of_days))
            for hour in range(0, 24)]
    return jsonify(data)


@app.route('/length_json')
def length_json():
    results = defaultdict(lambda: 0)
    results.update(session.query(
            func.char_length(db.History.cmd).label('length'),
            func.count('length')
        ).group_by('length').all())

    if not results:
        return jsonify({})

    flat_values = []
    for length, number in results.items():
        flat_values.extend([length] * number)

    data = {
        'average': float('%.2f' % statistics.mean(flat_values)),
        'median': statistics.median(flat_values),
        'series': [results[length]
                   for length in range(1, max(results.keys()) + 1)]
    }
    return jsonify(data)


@app.route('/markov_json')
def markov_json():
    words_2 = []
    w2 = None
    words = session.query(db.History.cmd).order_by(db.History.start).all()
    for word in words:
        w1, w2 = w2, word[0].split(' ')[0]
        words_2.append((w1, w2))
    counter = Counter(words_2).most_common(40)
    unique_words = set()
    for (w1, w2), count in counter:
        unique_words.add(w1)
        unique_words.add(w2)
    unique_words = list(unique_words)
    data = {
        'xCategories': unique_words,
        'yCategories': unique_words,
        'series': [
            [unique_words.index(w2), unique_words.index(w1), count]
            for (w1, w2), count in counter
        ]
    }
    return jsonify(data)


@app.route('/markov_full_json')
def markov_full_json():
    words_2 = []
    w2 = None
    words = session.query(db.History.cmd).order_by(db.History.start).all()
    for word in words:
        w1, w2 = w2, word[0]
        words_2.append((w1, w2))
    counter = Counter(words_2).most_common(40)
    unique_words = set()
    for (w1, w2), count in counter:
        unique_words.add(w1)
        unique_words.add(w2)
    unique_words = list(unique_words)
    data = {
        'xCategories': unique_words,
        'yCategories': unique_words,
        'series': [
            [unique_words.index(w2), unique_words.index(w1), count]
            for (w1, w2), count in counter
        ]
    }
    return jsonify(data)


@app.route('/monthly_json')
def monthly_json():
    results = defaultdict(lambda: 0)
    results.update(session.query(
            extract('month', db.History.start).label('month'),
            func.count('month')
        ).group_by('month').all())
    data = [results[month] for month in range(1, 13)]
    return jsonify(data)


@app.route('/monthly_average_json')
def monthly_average_json():
    mintime = session.query(func.min(db.History.start)).first()[0]
    maxtime = session.query(func.max(db.History.start)).first()[0]
    number_of_years = fractional_year(mintime, maxtime) + 1
    results = defaultdict(lambda: 0)
    results.update(session.query(
            extract('month', db.History.start).label('month'),
            func.count('month')
        ).group_by('month').all())
    data = [float('%.2f' % (results[month] / number_of_years))
            for month in range(1, 13)]
    return jsonify(data)


@app.route('/top_commands_full_json')
def top_commands_full_json():
    data = None
    return jsonify(data)


@app.route('/top_commands_json')
def top_commands_json():
    data = None
    return jsonify(data)


@app.route('/trending_json')
def trending_json():
    data = None
    return jsonify(data)


@app.route('/type_json')
def type_json():
    results = session.query(
        db.History.type,
        func.count(db.History.type)
    ).group_by(db.History.type).all()
    # total = sum(r[1] for r in results)
    data = [
        {'name': r[0] or 'none', 'y': r[1]}
        for r in sorted(results, key=lambda x: x[1], reverse=True)
    ]
    return jsonify(data)


@app.route('/wordcloud_json')
def wordcloud_json():
    results = session.query(db.History.cmd).order_by(func.random()).limit(100)
    text = ' '.join(r[0] for r in results.all())
    return jsonify(text)
