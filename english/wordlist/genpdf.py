import os
import sys
import shutil
import csv

original_cwd = os.getcwd()

d = os.path.dirname(sys.argv[0])
os.chdir(d)

TEMPLATE_BEGIN = r"""
\documentclass[a4paper, 11pt]{ctexart}

\input{../../../tex-templates/preamble.tex}
\usepackage{multicol}
\usepackage{enumitem}

\setlength{\columnsep}{1cm}

\title{考研英语单词本}
\author{RC}

\begin{document}

\maketitle
\thispagestyle{empty}

\clearpage
\phantom{s}
\thispagestyle{empty}

\clearpage
\setcounter{page}{1}

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
DST_WORDLIST = 'wordlist.tex'

tex_file = open(DST_WORDLIST, 'w', encoding='utf-8')
tex_file.write(TEMPLATE_BEGIN)

words = []

with open(SRC_WORDLIST, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i == 0:
            continue

        word = row[0]
        explanations = row[1].splitlines()

        if not word:
            continue

        words.append(word)
        tex_file.write(
            TEMPLATE_WORD.format(word=word,
                                 explanations=r' \\ '.join(explanations)))

tex_file.write(TEMPLATE_MID)
for w in words:
    tex_file.write(TEMPLATE_JUST_WORD.format(word=w))

tex_file.write(TEMPLATE_END)
tex_file.close()

cmd = f'xelatex -synctex=1 -interaction=nonstopmode -file-line-error -shell-escape "{DST_WORDLIST}"'
os.system(cmd)
os.system(cmd)

TO_REMOVE = [
    '_minted-list',
    '_minted-wordlist',
    'wordlist.synctex.gz',
    'wordlist.aux',
    'wordlist.log',
    'wordlist.out',
    'wordlist.thm',
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
