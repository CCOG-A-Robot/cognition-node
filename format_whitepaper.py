with open("WHITEPAPER_v0.3.md", "r") as f:
    text = f.read()

text = text.replace("---", "<hr>")
text = text.replace("## 1.", "<h2>1.")
text = text.replace("## 2.", "<h2>2.")
text = text.replace("## 3.", "<h2>3.")
text = text.replace("## 4.", "<h2>4.")
text = text.replace("## 5.", "<h2>5.")
text = text.replace("## 6.", "<h2>6.")
text = text.replace("## 7.", "<h2>7.")
text = text.replace("### ", "<h3>")
text = text.replace("**", "<b>")
import re
text = re.sub(r'# (.*)', r'<h1>\1</h1>', text)
text = re.sub(r'<h2>(.*)', r'<h2>\1</h2>', text)
text = re.sub(r'<h3>(.*)', r'<h3>\1</h3>', text)

paragraphs = text.split('\n\n')
html_paragraphs = []
for p in paragraphs:
    if not p.startswith('<h') and not p.startswith('<hr'):
        html_paragraphs.append('<p>' + p.replace('\n', '<br>') + '</p>')
    else:
        html_paragraphs.append(p)

body = '\n'.join(html_paragraphs)

html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Cognition Coin | Whitepaper</title>
    <style>
        body {{
            background-color: #000000;
            color: #00ff00;
            font-family: "Courier New", Courier, monospace;
            margin: 40px;
            line-height: 1.4;
        }}
        a {{
            color: #00ffff;
            text-decoration: underline;
        }}
        a:visited {{
            color: #ff00ff;
        }}
        h1, h2 {{
            color: #ffffff;
            border-bottom: 1px solid #00ff00;
            margin-top: 40px;
        }}
        h3 {{ color: #ffffff; }}
        .nav {{
            margin-bottom: 30px;
            padding: 10px;
            border: 1px dashed #00ff00;
        }}
    </style>
</head>
<body>

    <div class="nav">
        <strong>[ <a href="index.html">HOME</a> ] | [ <a href="roadmap.html">ROADMAP</a> ] | [ <a href="whitepaper.html">WHITEPAPER</a> ] | [ <a href="ledger.html">PUBLIC LEDGER</a> ] | [ <a href="forum/">BBS TERMINAL</a> ]</strong>
    </div>

    {body}

</body>
</html>"""

with open("public_website/whitepaper.html", "w") as f:
    f.write(html_template)
