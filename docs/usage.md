---
description: How to install chadwickpy and run the Chadwick tools on Retrosheet event files, including the chadwickpy umbrella command and python -m form.
---

# Install and use

```bash
pip install chadwickpy        # or: uv tool install chadwickpy
cwevent -y 2010 -f 0-96 2010NYA.EVA > 2010NYA.csv
cwgame -y 2010 2010NYA.EVA
chadwickpy cwbox -y 2010 2010NYA.EVA
python -m chadwickpy cwdaily -y 2010 2010NYA.EVA
```

Command names and options are Chadwick's. Roster files (`.ROS`, `TEAMyyyy`) are read from
the event file's directory. If the C programs are installed too, whichever is first on
`PATH` runs; `chadwickpy TOOL` always runs this package.

## Data

Get event files from [Retrosheet](https://www.retrosheet.org/game.htm). They are not
included in this package. If you publish anything built on them, include Retrosheet's notice
(see the project README).
