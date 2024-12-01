from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/terms')
def terms():
    terms_path = os.path.join(os.path.dirname(__file__), 'terms.txt')
    with open(terms_path, 'r', encoding='utf-8') as file:
        content = file.read()
    print("Terms content:", content)  # デバッグ用に出力
    return render_template('terms.html', terms_content=content)

if __name__ == '__main__':
    app.run(debug=True)
