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

SRC_WORDLIST = 'wordlist.csv'
DST_LF_WORDLIST = 'wordlist-low-freq.tex'
DST_HF_WORDLIST = 'wordlist-high-freq.tex'

lf_wordlist = open(DST_LF_WORDLIST, 'w', encoding='utf-8')
hf_wordlist = open(DST_HF_WORDLIST, 'w', encoding='utf-8')
lf_wordlist.write(TEMPLATE_BEGIN.replace('XXX', '低频词'))
hf_wordlist.write(TEMPLATE_BEGIN.replace('XXX', '高频词'))

lf_words = []
hf_words = []

with open(SRC_WORDLIST, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i == 0:
            continue

        word = row[0]
        explanations = row[1].splitlines()
        freq = 'L' if row[2] == '低' else 'H'

        if not word:
            continue

        fmt_args = {'word': word, 'explanations': r' \\ '.join(explanations)}
        if freq == 'L':
            lf_words.append(word)
            lf_wordlist.write(TEMPLATE_WORD.format(**fmt_args))
        else:
            hf_words.append(word)
            hf_wordlist.write(TEMPLATE_WORD.format(**fmt_args))

lf_wordlist.write(TEMPLATE_MID)
hf_wordlist.write(TEMPLATE_MID)

for w in lf_words:
    lf_wordlist.write(TEMPLATE_JUST_WORD.format(word=w))
for w in hf_words:
    hf_wordlist.write(TEMPLATE_JUST_WORD.format(word=w))

lf_wordlist.write(TEMPLATE_END)
hf_wordlist.write(TEMPLATE_END)
lf_wordlist.close()
hf_wordlist.close()

cmd = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape "{}"'
os.system(cmd.format(DST_LF_WORDLIST))
os.system(cmd.format(DST_LF_WORDLIST))
os.system(cmd.format(DST_HF_WORDLIST))
os.system(cmd.format(DST_HF_WORDLIST))

TO_REMOVE = [
    '_minted-wordlist-low-freq',
    '_minted-wordlist-high-freq',
    'wordlist-low-freq.synctex.gz',
    'wordlist-high-freq.synctex.gz',
    'wordlist-low-freq.aux',
    'wordlist-high-freq.aux',
    'wordlist-low-freq.log',
    'wordlist-high-freq.log',
    'wordlist-low-freq.out',
    'wordlist-high-freq.out',
    'wordlist-low-freq.thm',
    'wordlist-high-freq.thm',
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
