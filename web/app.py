import os
import random
from flask import Flask, request, render_template, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Fungsi untuk memeriksa apakah file valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Fungsi untuk menghitung Jaro-Winkler similarity
def jaro_similarity(s1, s2):
    s1_len, s2_len = len(s1), len(s2)
    if s1_len == 0 and s2_len == 0:
        return 1.0

    match_distance = (max(s1_len, s2_len) // 2) - 1
    s1_matches = [False] * s1_len
    s2_matches = [False] * s2_len
    matches = 0
    transpositions = 0

    for i in range(s1_len):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, s2_len)
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    s1_m = [s1[i] for i in range(s1_len) if s1_matches[i]]
    s2_m = [s2[j] for j in range(s2_len) if s2_matches[j]]

    for i in range(len(s1_m)):
        if s1_m[i] != s2_m[i]:
            transpositions += 1

    transpositions //= 2
    return (matches / s1_len + matches / s2_len + (matches - transpositions) / matches) / 3


def jaro_winkler_similarity(s1, s2, p=0.1, max_l=4):
    jaro_sim = jaro_similarity(s1, s2)
    prefix = 0
    for i in range(min(len(s1), len(s2))):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
        if prefix == max_l:
            break
    return jaro_sim + (prefix * p * (1 - jaro_sim))


# Fungsi untuk memproses dataset dan melakukan swapping pada sensitive itemsets
def process_and_swap_sensitive_items(content):
    sensitive_itemsets = [
        (214, 763),
        (778, 195, 385),
        (12, 934),
        (359, 282),
        (16, 898, 1368),
        (1299, 557),
        (1336, 128, 224, 667),
        (1440, 1350),
        (1222, 354, 1502),
        (110, 1419, 610, 1065),
        (890, 1399, 284),
        (1195, 1478, 629),
        (615, 459),
        (1187, 977, 1193),
        (907, 1202, 1046),
        (487, 570),
        (551, 1206, 384),
        (1432, 251),
        (69, 1444),
        (11, 1213, 1136)
    ]

    # Konversi dataset ke list
    dataset = [list(map(int, line.split())) for line in content if line.strip()]
    dataset_strings = [" ".join(map(str, row)) for row in dataset]

    # Identifikasi baris sensitif
    sensitive_rows = []
    for idx, row in enumerate(dataset):
        for itemset in sensitive_itemsets:
            if all(item in row for item in itemset):
                sensitive_rows.append(idx)
                break

    # Hitung kemiripan dan tentukan swap candidates
    sensitive_swapping_results = []
    for sens_row_idx in sensitive_rows:
        sens_row = dataset_strings[sens_row_idx]
        min_similarity = 1.0
        swap_candidate_idx = None

        for idx, row_str in enumerate(dataset_strings):
            if idx == sens_row_idx:
                continue
            similarity = jaro_winkler_similarity(sens_row, row_str)
            if similarity < min_similarity:
                min_similarity = similarity
                swap_candidate_idx = idx

        sensitive_swapping_results.append((sens_row_idx, swap_candidate_idx, min_similarity))

    # Lakukan swapping
    for sens_row_idx, swap_candidate_idx, _ in sensitive_swapping_results:
        sens_row = dataset[sens_row_idx]
        swap_row = dataset[swap_candidate_idx]

        sens_itemset = next(itemset for itemset in sensitive_itemsets if all(item in sens_row for item in itemset))
        sens_item = sens_itemset[0]
        swap_item = swap_row[0]

        sens_row[sens_row.index(sens_item)] = swap_item
        swap_row[swap_row.index(swap_item)] = sens_item

    return dataset


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with open(filepath, 'r') as f:
                content = f.readlines()

            if not content:
                return "File is empty", 400

            modified_dataset = process_and_swap_sensitive_items(content)

            # Simpan dataset hasil modifikasi
            modified_filename = f"modified_{filename}"
            modified_filepath = os.path.join(app.config['UPLOAD_FOLDER'], modified_filename)
            with open(modified_filepath, 'w') as f:
                for row in modified_dataset:
                    f.write(" ".join(map(str, row)) + '\n')

            return send_file(modified_filepath, as_attachment=True, download_name=modified_filename)

    return render_template('index.html')


@app.route('/compare', methods=['POST'])
def compare_files():
    if request.method == 'POST':
        original_file = request.files['original_file']
        modified_file = request.files['modified_file']

        if original_file and allowed_file(original_file.filename) and modified_file and allowed_file(modified_file.filename):
            original_filename = secure_filename(original_file.filename)
            modified_filename = secure_filename(modified_file.filename)
            original_filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            modified_filepath = os.path.join(app.config['UPLOAD_FOLDER'], modified_filename)
            original_file.save(original_filepath)
            modified_file.save(modified_filepath)

            with open(original_filepath, 'r') as f1, open(modified_filepath, 'r') as f2:
                original_lines = f1.readlines()
                modified_lines = f2.readlines()

            if len(original_lines) != len(modified_lines):
                return "File tidak memiliki jumlah baris yang sama.", 400

            comparisons = []
            total_similarity_score = 0
            for i, (line1, line2) in enumerate(zip(original_lines, modified_lines)):
                similarity_score = jaro_winkler_similarity(line1.strip(), line2.strip())
                total_similarity_score += similarity_score
                comparisons.append({
                    'line_number': i + 1,
                    'original': line1.strip(),
                    'modified': line2.strip(),
                    'similarity_score': similarity_score,
                    'is_similar': similarity_score > 0.85  
                })

            overall_similarity_score = total_similarity_score / len(comparisons)

            return render_template('comparison_results.html', comparisons=comparisons, overall_similarity_score=overall_similarity_score)

    return "Error: File tidak sesuai atau tidak ditemukan.", 400


if __name__ == '__main__':
    app.run(debug=True)
