import os
import sys
import shutil
import csv

original_cwd = os.getcwd()

d = os.path.dirname(sys.argv[0])
os.chdir(d)

TEMPLATE_BEGIN = r"""
\documentclass[b5paper, 11pt]{ctexart}

\input{../../../tex-templates/preamble.tex}
\usepackage{multicol}
\usepackage{enumitem}

\setlength{\columnsep}{1cm}

\title{考研英语词汇 - XXX}
\author{RC}

\begin{document}

\begin{multicols*}{2}
    \begin{description}[leftmargin=0.5cm]
"""

TEMPLATE_MID = r"""
    \end{description}
\end{multicols*}

\clearpage

\begin{multicols*}{3}
    \begin{description}
"""

TEMPLATE_END = r"""
    \end{description}
\end{multicols*}

\end{document}
"""

TEMPLATE_WORD = r"""
\item[{word}] \hfill \\ {explanations}
"""

TEMPLATE_JUST_WORD = r"""
\item[{word}]
"""

SRC_WORDLIST = 'wordlist1.csv'
DST_HF_WORDLIST = 'wordlist1.tex'

wordlist = open(DST_HF_WORDLIST, 'w', encoding='utf-8')
wordlist.write(TEMPLATE_BEGIN.replace('XXX', '遗忘词'))

words = []

with open(SRC_WORDLIST, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i == 0:
            continue

        word = row[0]
        explanations = row[1].splitlines()
        ok = row[2] != '低' and row[3].strip() in ['?', 'x']

        if not word:
            continue

        fmt_args = {'word': word, 'explanations': r' \\ '.join(explanations)}
        if ok:
            words.append(word)
            wordlist.write(TEMPLATE_WORD.format(**fmt_args))

wordlist.write(TEMPLATE_MID)

for w in words:
    wordlist.write(TEMPLATE_JUST_WORD.format(word=w))

wordlist.write(TEMPLATE_END)
wordlist.write(TEMPLATE_END)
wordlist.close()
wordlist.close()

cmd = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape "{}"'
os.system(cmd.format(DST_HF_WORDLIST))
os.system(cmd.format(DST_HF_WORDLIST))

TO_REMOVE = [
    '_minted-wordlist1',
    'wordlist1.synctex.gz',
    'wordlist1.aux',
    'wordlist1.log',
    'wordlist1.out',
    'wordlist1.thm',
]

for file in TO_REMOVE:
    if os.path.isdir(file):
        shutil.rmtree(file, ignore_errors=True)
    elif os.path.isfile(file):
        try:
            os.remove(file)
        except:
            pass

os.chdir(original_cwd)
