# app.py
from flask import Flask, request, render_template, send_from_directory
import os
import glob
from findsimilar import make_database_list, read_query_sgf, calc_similarity

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE_FOLDER'] = 'database'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    num_moves = int(request.form['num_moves'])
    sgf_file = request.files['sgf_file']

    # Save the uploaded SGF file
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    sgf_file_path = os.path.join(app.config['UPLOAD_FOLDER'], sgf_file.filename)
    sgf_file.save(sgf_file_path)

    # paths of database and query sgf file
    database_path = os.path.normpath(app.config['DATABASE_FOLDER'])
    query_sgf_path = sgf_file_path

    # make database
    path_list = glob.glob(os.path.join(database_path, "*"))
    database = make_database_list(path_list, num_moves)

    # make 16-type variations of moves from query sgf
    query_moves = read_query_sgf(query_sgf_path, num_moves)

    # Calculate similarity
    similarity = calc_similarity(query_moves, database)

    # re-sorted database by similarity in decreasing order
    temp = [[str1, var1] for str1, var1 in zip(path_list, similarity)]
    result = sorted(temp, key=lambda x: x[1], reverse=True)

    # Get top 10 results
    top_10_results = result[:10]

    return render_template('results.html', results=top_10_results, os=os)

@app.route('/database/<filename>')
def database_file(filename):
    return send_from_directory(app.config['DATABASE_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)