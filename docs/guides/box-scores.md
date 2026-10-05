---
description: Generate readable text, XML or SportsML box scores from Retrosheet event files with chadwickpy's cwbox command.
---

# Box scores (`cwbox`)

```bash
cwbox -q -y 2007 2007TST.EVA
```

```text
     Game of 5/31/2007 -- Chicago at Toronto (N)

  Chicago            AB  R  H RBI    Toronto            AB  R  H RBI
Erstad D, cf          3  0  0  0   Rios A, rf            3  0  0  0
Terrero L, ph-cf      1  0  0  0   Overbay L, 1b         3  0  0  0
Iguchi T, 2b          4  0  1  0   Wells V, cf           3  0  0  0
...
Chicago          000 000 000 --  0
Toronto          010 000 01x --  2

  Chicago              IP  H  R ER BB SO
Buehrle M (L)         8.0  2  2  2  0  6
...
HR -- Hill A, Thomas F
T -- 1:50
A -- 22436
```

| Option | Effect |
|---|---|
| (none) | plain-text box score |
| `-X` | XML |
| `-S` | SportsML |
| `-i`, `-s`, `-e`, `-y`, `-q` | same filters as the other tools |

`cwbox` reads the roster files for player names, so run it from the folder that holds `TEAMyyyy` and the `.ROS` files (the current folder, as in Chadwick).
