/* API-level checks for book.c, roster.c, file.c, game.c writer and the cwtools XML writer.
 * usage: final_a_dump MODE ARGS...
 *   atoi STRING            cw_atoi(STRING, NULL): prints the result (warnings go to stderr)
 *   rosterfind FILE ID     cw_roster_player_find(r, NULL) and (r, ID)
 *   infonull               a game with an info record without data, written with cw_game_write
 *   book FILE SCRIPT       scorebook edits (ops below), one result line per op
 *   xml SCRIPT             XML writer calls (ops below), output is the document
 * book ops (tab separated): new ID DATE NUMBER ("-" = no such info record) | insertnull |
 *   appendnull | iter MODE | remove ID | dump
 * xml ops: open P NAME | close N | cdata N TEXT | attr N A V | attri N A INT | attrp N A INT |
 *   attrf N A V | cleanup           (nodes are numbered from 0 = root, in order of "open") */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "chadwick.h"
#include "xmlwrite.h"

static int split(char *line, char **f) {
  int n = 0; char *p = line;
  f[n++] = p;
  for (; *p; p++) if (*p == '\t') { *p = 0; f[n++] = p + 1; if (n >= 8) break; }
  return n;
}

static int last_digit_zero(CWGame *g) { return g->game_id[strlen(g->game_id) - 1] == '0'; }

static void dump_book(CWScorebook *b) {
  for (CWGame *g = b->first_game; g; g = g->next) printf("%s\n", g->game_id);
}

static void run_book(const char *path, const char *script) {
  FILE *fp = fopen(path, "r");
  CWScorebook *b = cw_scorebook_create();
  int n = cw_scorebook_read(b, fp);
  char line[4096], *f[8];
  FILE *sp = fopen(script, "r");
  printf("read=%d\n", n);
  while (fgets(line, sizeof line, sp)) {
    char *nl = strchr(line, '\n'); if (nl) *nl = 0;
    split(line, f);
    if (!strcmp(f[0], "new")) {
      CWGame *g = cw_game_create(f[1]);
      if (strcmp(f[2], "-")) cw_game_info_append(g, "date", f[2]);
      if (strcmp(f[3], "-")) cw_game_info_append(g, "number", f[3]);
      printf("insert=%d\n", cw_scorebook_insert_game(b, g));
    } else if (!strcmp(f[0], "insertnull")) printf("insert=%d\n", cw_scorebook_insert_game(b, NULL));
    else if (!strcmp(f[0], "appendnull")) printf("append=%d\n", cw_scorebook_append_game(b, NULL));
    else if (!strcmp(f[0], "iter")) {
      CWScorebookIterator *it = cw_scorebook_iterate(b, atoi(f[1]) ? last_digit_zero : NULL);
      CWGame *g;
      while ((g = cw_scorebook_iterator_next(it))) printf("it %s\n", g->game_id);
    } else if (!strcmp(f[0], "remove")) {
      CWGame *g = cw_scorebook_remove_game(b, f[1]);
      printf("removed=%s\n", g ? g->game_id : "(none)");
    } else if (!strcmp(f[0], "dump")) dump_book(b);
    fflush(stdout);
  }
}

static void run_xml(const char *script) {
  XMLDoc *doc = xml_document_create(stdout, "root");
  XMLNode *nodes[256]; int count = 1;
  char line[4096], *f[8];
  FILE *sp = fopen(script, "r");
  nodes[0] = doc->root;
  while (fgets(line, sizeof line, sp)) {
    char *nl = strchr(line, '\n'); if (nl) *nl = 0;
    split(line, f);
    if (!strcmp(f[0], "open")) nodes[count++] = xml_node_open(nodes[atoi(f[1])], strdup(f[2]));
    else if (!strcmp(f[0], "close")) xml_node_close(nodes[atoi(f[1])]);
    else if (!strcmp(f[0], "cdata")) xml_node_cdata(nodes[atoi(f[1])], f[2]);
    else if (!strcmp(f[0], "attr")) xml_node_attribute(nodes[atoi(f[1])], f[2], f[3]);
    else if (!strcmp(f[0], "attri")) xml_node_attribute_int(nodes[atoi(f[1])], f[2], atoi(f[3]));
    else if (!strcmp(f[0], "attrp")) xml_node_attribute_posint(nodes[atoi(f[1])], f[2], atoi(f[3]));
    else if (!strcmp(f[0], "attrf")) xml_node_attribute_fmt(nodes[atoi(f[1])], f[2], "%s", f[3]);
    else if (!strcmp(f[0], "cleanup")) xml_document_cleanup(doc);
  }
  fflush(stdout);
}

int main(int argc, char **argv) {
  const char *mode = argv[1];
  if (!strcmp(mode, "atoi")) printf("%d\n", cw_atoi(argv[2], NULL));
  else if (!strcmp(mode, "rosterfind")) {
    CWRoster *r = cw_roster_create("T", 0, "L", "C", "N");
    cw_roster_read(r, fopen(argv[2], "r"));
    CWPlayer *p = cw_roster_player_find(r, argv[3]);
    printf("null=%d known=%s\n", cw_roster_player_find(r, NULL) == NULL, p ? p->player_id : "(none)");
  } else if (!strcmp(mode, "infonull")) {
    CWGame *g = cw_game_create("X");
    cw_game_set_version(g, "2");
    cw_game_info_append(g, "foo", NULL);
    cw_game_write(g, stdout);
  } else if (!strcmp(mode, "book")) run_book(argv[2], argv[3]);
  else if (!strcmp(mode, "xml")) run_xml(argv[2]);
  return 0;
}
